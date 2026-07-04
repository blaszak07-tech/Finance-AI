"""Full tool-loop agent — the autonomous rung above orchestrator-workers.

Unlike the Agents tab (one fixed routing decision), this agent runs in a LOOP: it's
given tools, decides which to call, SEES the result, and decides its next action —
repeating until it judges it has enough to answer. The model drives its own trajectory.

Pattern (Anthropic tool use):
  1. send messages + tool definitions to Claude
  2. if Claude returns tool_use blocks → execute them, append tool_result, loop
  3. if Claude returns a plain answer (stop_reason != "tool_use") → done

Tools reuse the capabilities we already built (search, profile, specialists).
"""

import json
from src.llm import _client, DEFAULT_MODEL, call
from src.search import build_index, search_index
from src.profile import profile_summary
from src.agents import SPECIALISTS, SPECIALIST_USER, _format_history
from src.mcp_bridge import list_mcp_tools, call_mcp_tool

_mcp_cache = None


def _mcp_tools() -> list[dict]:
    """MCP-served tools (finance calculators), discovered once and cached."""
    global _mcp_cache
    if _mcp_cache is None:
        _mcp_cache = list_mcp_tools()
    return _mcp_cache

TOOLS = [
    {
        "name": "search_history",
        "description": "Semantic search over this client's past meeting records. Returns the most "
                       "relevant passages with their meeting dates. Use it to find what was discussed before.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for, in natural language."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_profile",
        "description": "Get the known structured profile facts about this client (age, goals, risk "
                       "tolerance, assets, etc.). No input needed.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_specialist",
        "description": "Consult a specialist financial analyst about the client's situation. Returns "
                       "that specialist's flags and considerations in their domain.",
        "input_schema": {
            "type": "object",
            "properties": {
                "specialist": {
                    "type": "string",
                    "enum": ["retirement", "tax", "risk"],
                    "description": "Which specialist to consult.",
                },
            },
            "required": ["specialist"],
        },
    },
]

AGENT_SYSTEM = """You are an autonomous wealth management analyst for one specific client. You have tools
to search the client's meeting history, fetch their profile, consult specialist analysts (retirement, tax,
risk), and run exact finance calculators (future value, retirement projection, required savings, safe
withdrawal income).

Work step by step. Gather what you genuinely need with tools, then give a clear, grounded final answer.
Use the calculators for any math rather than estimating figures yourself. Cite meeting dates when you rely
on history. Don't call a tool if you already have the information. As soon as you can answer well, stop
calling tools and write the final answer."""


def _execute_tool(name: str, tool_input: dict, client_id: str, index: tuple, question: str) -> str:
    if name in {t["name"] for t in _mcp_tools()}:
        return call_mcp_tool(name, tool_input)

    chunks, embeddings = index
    if name == "search_history":
        if not len(chunks):
            return "No past meeting history is on file for this client."
        hits = search_index(chunks, embeddings, tool_input.get("query", question), top_k=4)
        return "\n\n".join(f"[{h['timestamp']}] {h['text']}" for h in hits) or "No relevant passages found."
    if name == "get_profile":
        return profile_summary(client_id)
    if name == "run_specialist":
        key = tool_input.get("specialist")
        spec = SPECIALISTS.get(key)
        if not spec:
            return f"Unknown specialist '{key}'. Valid: retirement, tax, risk."
        hits = []
        if len(chunks):
            hits = search_index(chunks, embeddings, f"{spec['retrieval_query']}. {question}", top_k=3)
        return call(
            prompt=SPECIALIST_USER.format(
                notes=question, profile=profile_summary(client_id),
                history=_format_history(hits), label=spec["label"],
            ),
            system=spec["system"],
        )
    return f"Unknown tool '{name}'."


def available_tools() -> dict:
    """Tool names grouped by source, for display."""
    return {
        "built-in": [t["name"] for t in TOOLS],
        "MCP server": [t["name"] for t in _mcp_tools()],
    }


def run_agent(client_id: str, question: str, index: tuple | None = None, max_steps: int = 6) -> dict:
    """Run the tool-use loop. Returns {answer, steps} where steps is the trace of the
    agent's thoughts and tool actions (for the educational view)."""
    if index is None:
        index = build_index(client_id)

    messages = [{"role": "user", "content": f"Question about this client: {question}"}]
    steps: list[dict] = []
    all_tools = TOOLS + _mcp_tools()

    for _ in range(max_steps):
        response = _client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1500,
            system=AGENT_SYSTEM,
            tools=all_tools,
            messages=messages,
        )
        assistant_text = "".join(b.text for b in response.content if b.type == "text").strip()
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason != "tool_use":
            return {"answer": assistant_text, "steps": steps}

        if assistant_text:
            steps.append({"type": "thought", "text": assistant_text})

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for tu in tool_uses:
            result = _execute_tool(tu.name, tu.input, client_id, index, question)
            steps.append({"type": "action", "tool": tu.name, "input": tu.input, "result": result})
            tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": result})
        messages.append({"role": "user", "content": tool_results})

    # Hit the step limit — force a final answer with no more tools
    messages.append({"role": "user", "content": "Give your best final answer now from what you've gathered."})
    final = _client.messages.create(model=DEFAULT_MODEL, max_tokens=1500, system=AGENT_SYSTEM, messages=messages)
    final_text = "".join(b.text for b in final.content if b.type == "text").strip()
    return {"answer": final_text, "steps": steps}
