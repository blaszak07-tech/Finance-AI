"""A real MCP (Model Context Protocol) server exposing deterministic finance calculators.

MCP is the open standard for giving an LLM tools/data via a separate server process. This server is
self-contained (no app imports) and speaks MCP over stdio. The tool-loop agent connects to it as a
client (see mcp_bridge.py), discovers these tools at runtime, and can call them — so the agent gets
exact arithmetic instead of hallucinating numbers.

Run directly for a stdio MCP server:  python3 src/mcp_server.py
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("finance-calculators")


@mcp.tool()
def future_value(present_value: float, annual_return_pct: float, years: float) -> str:
    """Project the future value of a single lump sum that grows at a fixed annual return.
    present_value: today's amount in dollars. annual_return_pct: e.g. 6 for 6%. years: number of years."""
    fv = present_value * (1 + annual_return_pct / 100) ** years
    return f"Future value: ${fv:,.0f} (from ${present_value:,.0f} at {annual_return_pct}% over {years:g} years)"


@mcp.tool()
def retirement_projection(current_savings: float, annual_contribution: float,
                          annual_return_pct: float, years: float) -> str:
    """Project a retirement balance: grow current savings AND add yearly contributions, at a fixed return.
    Returns the projected nest egg at the end of the period."""
    r = annual_return_pct / 100
    grown = current_savings * (1 + r) ** years
    contrib_fv = annual_contribution * (((1 + r) ** years - 1) / r) if r else annual_contribution * years
    total = grown + contrib_fv
    return (f"Projected balance in {years:g} years: ${total:,.0f} "
            f"(current ${current_savings:,.0f} grows to ${grown:,.0f}; "
            f"${annual_contribution:,.0f}/yr contributions add ${contrib_fv:,.0f}, at {annual_return_pct}%)")


@mcp.tool()
def savings_needed(target_amount: float, annual_return_pct: float, years: float) -> str:
    """Required ANNUAL contribution to reach a target amount in a set number of years at a fixed return."""
    r = annual_return_pct / 100
    factor = (((1 + r) ** years - 1) / r) if r else years
    pmt = target_amount / factor if factor else target_amount
    return f"To reach ${target_amount:,.0f} in {years:g} years at {annual_return_pct}%, save ${pmt:,.0f}/year."


@mcp.tool()
def safe_withdrawal_income(portfolio_value: float, withdrawal_rate_pct: float = 4.0) -> str:
    """Estimate sustainable annual retirement income from a portfolio using a safe withdrawal rate
    (default 4%). Returns annual and monthly income."""
    annual = portfolio_value * withdrawal_rate_pct / 100
    return (f"At a {withdrawal_rate_pct}% withdrawal rate, ${portfolio_value:,.0f} supports "
            f"${annual:,.0f}/year (${annual / 12:,.0f}/month).")


if __name__ == "__main__":
    mcp.run()
