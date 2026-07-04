# V3 — Real-time voice meeting

Talk to an AI wealth advisor **in real time**, in your browser, with **barge-in** (interrupt it
mid-sentence). Everything runs locally and free except Claude tokens.

```
browser mic → WebRTC → Silero VAD (turn-taking) → MLX Whisper (STT)
    → Claude Haiku → Kokoro (TTS) → WebRTC → your speakers
```

This runs **outside** Streamlit (Streamlit can't do full-duplex audio) but **shares the same
`data/` store** — when you hang up, the conversation runs through the normal pipeline and is saved
to that client's history, so it appears in the Streamlit app like any other meeting.

## One-time setup
```
pip3 install -r requirements-live.txt
```
(macOS Apple Silicon — uses MLX. The first run downloads the Whisper + Kokoro models, ~1 min.)

## Run
```
WM_LIVE_CLIENT="John Smith" python3 live/bot.py
```
Then open the printed URL (**http://localhost:7860**), click to connect, allow mic access, and talk.
Hang up (or close the tab) to end — the meeting saves to `John Smith`'s history.

- `WM_LIVE_CLIENT` sets which client the meeting is filed under (default: "Live Client").
- The AI plays the **advisor**; you play the **client**. Just talk naturally — and interrupt whenever.

## Notes
- First response after connecting may lag a few seconds while models load; after that it's ~1.5–2.5s/turn.
- Voices are Kokoro (free, local) — good, not lifelike. Swappable for ElevenLabs later if the budget changes.
- Real-time is genuinely interruptible thanks to Silero VAD; talk over it and it stops.
