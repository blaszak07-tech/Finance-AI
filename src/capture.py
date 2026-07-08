"""Local live-meeting audio capture (V4) — free, platform-agnostic.

Records from an input device using sounddevice. Paired with a BlackHole aggregate device (mic +
system audio), this captures BOTH sides of any Zoom/Meet/Teams call happening on the machine. All the
device's input channels are captured and downmixed to mono, so whatever the aggregate device exposes
(your mic + the other party via BlackHole) ends up in one stream Whisper can transcribe.

One recording at a time (single local user). Start/stop are driven by the API.
"""

import time
import tempfile
import numpy as np


def list_input_devices() -> list[dict]:
    import sounddevice as sd
    devices = sd.query_devices()
    return [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]


class _Recorder:
    def __init__(self, device: int):
        import sounddevice as sd
        import soundfile as sf

        info = sd.query_devices(device, "input")
        self.samplerate = int(info["default_samplerate"])
        self.channels = min(int(info["max_input_channels"]), 8)
        self.path = tempfile.mktemp(suffix=".wav")
        self.started = time.time()
        self._sf = sf.SoundFile(self.path, mode="w", samplerate=self.samplerate, channels=1, subtype="PCM_16")

        def callback(indata, frames, time_info, status):
            # Downmix every channel (mic + system audio) into mono
            mono = indata if indata.shape[1] == 1 else indata.mean(axis=1, keepdims=True)
            self._sf.write(mono)

        self._stream = sd.InputStream(
            samplerate=self.samplerate, device=device, channels=self.channels,
            dtype="float32", callback=callback,
        )

    def start(self):
        self._stream.start()

    def stop(self) -> str:
        self._stream.stop()
        self._stream.close()
        self._sf.close()
        return self.path


_rec: _Recorder | None = None


def start(device: int) -> None:
    global _rec
    if _rec is not None:
        raise RuntimeError("A recording is already in progress.")
    _rec = _Recorder(int(device))
    _rec.start()


def stop() -> str:
    """Stop recording and return the path to the captured WAV."""
    global _rec
    if _rec is None:
        raise RuntimeError("No recording in progress.")
    path = _rec.stop()
    _rec = None
    return path


def status() -> dict:
    return {"recording": _rec is not None, "elapsed": time.time() - _rec.started if _rec else 0}
