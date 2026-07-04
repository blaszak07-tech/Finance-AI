"""V3 — real-time, interruptible voice meeting (Pipecat + all-local models).

You talk to an AI wealth advisor in real time through your browser, with barge-in (interrupt it
mid-sentence). Everything runs locally and free except Claude tokens:

    browser mic → WebRTC → Silero VAD (turn-taking/barge-in) → MLX Whisper (STT)
        → Claude (Haiku) → Kokoro (TTS) → WebRTC → your speakers

When you hang up, the conversation is run through the same pipeline as every other meeting and saved
to this client's history, so it shows up in the Streamlit app.

This lives OUTSIDE Streamlit (Streamlit can't do full-duplex audio) but SHARES the same data/ store.

Run:
    WM_LIVE_CLIENT="John Smith" python3 live/bot.py
then open the URL it prints (http://localhost:7860).
"""

import os
import sys
import asyncio

# Make the app's src/ importable when run as a standalone script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Use certifi's CA bundle so model/data downloads over HTTPS work on macOS Python
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.pipeline.runner import PipelineRunner
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.services.whisper.stt import WhisperSTTServiceMLX, MLXModel
from pipecat.services.anthropic.llm import AnthropicLLMService
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.frames.frames import LLMRunFrame
from pipecat.runner.types import SmallWebRTCRunnerArguments

from src.chain import run_chain
from src.storage import save_meeting

# --- Config (via env) -------------------------------------------------
_raw_client = os.environ.get("WM_LIVE_CLIENT", "Live Client").strip()
CLIENT_ID = _raw_client.lower().replace(" ", "_") or "live_client"

SEED_USER = "(I just joined the call.)"

ADVISOR_SYSTEM = """You are a warm, professional wealth management advisor on a live voice call with a client.
This is spoken conversation, so:
- Keep every reply SHORT — one to three sentences. Never monologue; it's a dialogue.
- Speak naturally, like a real person on a call. No stage directions, no bullet points, no markdown.
- Ask one focused follow-up at a time. Listen, react to what they actually said.
- Open by greeting them warmly and asking what they'd like to focus on today.
Never mention being an AI."""


def _flatten(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
            elif isinstance(c, str):
                parts.append(c)
        return " ".join(parts)
    return ""


def _extract_transcript(context: LLMContext) -> str:
    lines = []
    for m in context.messages:
        role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
        if role == "system":
            continue
        text = _flatten(content).strip()
        if not text or text == SEED_USER:
            continue
        speaker = "Advisor" if role == "assistant" else "Client"
        lines.append(f"{speaker}: {text}")
    return "\n\n".join(lines)


def _save_meeting(transcript: str):
    """Blocking — run the pipeline and persist. Called in an executor so it doesn't block the loop."""
    try:
        result = run_chain(CLIENT_ID, transcript)
        save_meeting(CLIENT_ID, {"notes": transcript, **result})
        print(f"[live] Saved meeting for '{CLIENT_ID}' — summary accuracy "
              f"{result.get('accuracy', {}).get('accuracy')}/100")
    except Exception as e:
        print(f"[live] Failed to save meeting: {e}")


async def bot(runner_args: SmallWebRTCRunnerArguments):
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    stt = WhisperSTTServiceMLX(model=MLXModel.LARGE_V3_TURBO)
    llm = AnthropicLLMService(api_key=os.environ["ANTHROPIC_API_KEY"], model="claude-haiku-4-5")
    tts = KokoroTTSService()

    context = LLMContext([
        {"role": "system", "content": ADVISOR_SYSTEM},
        {"role": "user", "content": SEED_USER},
    ])
    aggregators = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        aggregators.user(),
        llm,
        tts,
        transport.output(),
        aggregators.assistant(),
    ])

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True, enable_metrics=True))

    @transport.event_handler("on_client_connected")
    async def _on_connected(_transport, _client):
        print(f"[live] Client connected — advisor greeting (client_id='{CLIENT_ID}')")
        await task.queue_frames([LLMRunFrame()])  # make the advisor speak first

    @transport.event_handler("on_client_disconnected")
    async def _on_disconnected(_transport, _client):
        print("[live] Client disconnected — saving meeting to history")
        transcript = _extract_transcript(context)
        if transcript.strip():
            await asyncio.get_event_loop().run_in_executor(None, _save_meeting, transcript)
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)
    await runner.run(task)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
