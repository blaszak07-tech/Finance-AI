"""Voice I/O — all free/local. macOS `say` for text-to-speech, faster-whisper for
speech-to-text. This is a thin I/O layer around the existing text engine; the AI logic
(ai_reply / run_chain) is untouched. Swap these components later for nicer voices or
real-time streaming without changing the rest of the app."""

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

# Distinct macOS system voices per role
ADVISOR_VOICE = "Daniel"     # en_GB male
CLIENT_VOICE = "Samantha"    # en_US female
DATA_FORMAT = "LEI16@22050"  # 16-bit PCM, 22.05kHz — produces a stdlib-readable WAV

_whisper_model = None


# ── Text to speech ───────────────────────────────────────────
def _say_to_wav(text: str, voice: str, out_path: str) -> str:
    subprocess.run(
        ["say", "-v", voice, "-o", out_path, f"--data-format={DATA_FORMAT}", text],
        check=True,
    )
    return out_path


def _wav_duration(path: str) -> float:
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def speak(text: str, role: str) -> bytes:
    """Synthesize one line of speech and return WAV bytes."""
    voice = ADVISOR_VOICE if role == "Advisor" else CLIENT_VOICE
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        _say_to_wav(text, voice, tmp.name)
        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp.name)


def fmt_timestamp(seconds: float) -> str:
    """0 -> '00:00:00'."""
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def synthesize_conversation(turns: list[dict]) -> tuple[bytes, list[dict]]:
    """Voice a full conversation. Returns (combined WAV bytes, timed transcript).
    turns: [{"role": "Advisor"|"Client", "text": ...}, ...]
    timed: same turns plus a cumulative "timestamp" string starting at 00:00:00."""
    tmpdir = tempfile.mkdtemp()
    try:
        clip_paths = []
        timed = []
        cumulative = 0.0
        for i, turn in enumerate(turns):
            voice = ADVISOR_VOICE if turn["role"] == "Advisor" else CLIENT_VOICE
            path = os.path.join(tmpdir, f"{i}.wav")
            _say_to_wav(turn["text"], voice, path)
            clip_paths.append(path)
            timed.append({
                "timestamp": fmt_timestamp(cumulative),
                "role": turn["role"],
                "text": turn["text"],
            })
            cumulative += _wav_duration(path)

        combined = os.path.join(tmpdir, "combined.wav")
        with wave.open(clip_paths[0]) as first:
            params = first.getparams()
        with wave.open(combined, "wb") as out:
            out.setparams(params)
            for p in clip_paths:
                with wave.open(p) as w:
                    out.writeframes(w.readframes(w.getnframes()))

        with open(combined, "rb") as f:
            return f.read(), timed
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ── Speech to text ───────────────────────────────────────────
def _get_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def transcribe(wav_bytes: bytes) -> str:
    """Transcribe recorded WAV bytes to text using local faster-whisper."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(wav_bytes)
    tmp.close()
    try:
        segments, _ = _get_model().transcribe(tmp.name)
        return " ".join(s.text for s in segments).strip()
    finally:
        os.unlink(tmp.name)


def transcribe_file(path: str) -> str:
    """Transcribe a WAV file on disk (used for full-meeting live captures)."""
    segments, _ = _get_model().transcribe(path)
    return " ".join(s.text for s in segments).strip()
