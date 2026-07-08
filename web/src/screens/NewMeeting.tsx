import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { ClientDetail } from "../types";
import { TopBar, Page } from "../Shell";
import { Card, Button, Eyebrow, Spinner, TextArea, Field } from "../ui";

type Mode = null | "paste" | "live" | "simulate";

const PRESETS = [
  {
    label: "Pre-retiree, market-anxious",
    age: 58,
    situation: "Manufacturing manager, ~$1.1M in a 401k and a small pension. Single income.",
    concerns: "Wants to retire in 3 years, nervous a downturn wipes out the timeline.",
    risk: "conservative",
  },
  {
    label: "Liquidity event",
    age: 51,
    situation: "Sold a business, ~$4M in cash after tax. Spouse still works.",
    concerns: "Worried about the tax hit, wants to retire by 58, unsure how to deploy the cash.",
    risk: "moderate",
  },
  {
    label: "Young high earner",
    age: 34,
    situation: "Software engineer, ~$280k salary plus RSUs, lots of company stock.",
    concerns: "Concentration in employer stock, wants to buy a home, first time with an advisor.",
    risk: "aggressive",
  },
];

function OptionCard({
  title,
  desc,
  active,
  onClick,
  soon,
}: {
  title: string;
  desc: string;
  active: boolean;
  onClick: () => void;
  soon?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-5 text-left transition-colors ${
        active ? "border-gilt bg-raised" : "border-line bg-surface hover:border-gilt/50"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-paper">{title}</span>
        {soon && (
          <span className="rounded-full border border-line px-2 py-0.5 text-[10px] uppercase tracking-wider text-mute">
            Soon
          </span>
        )}
      </div>
      <p className="mt-1.5 text-sm text-mist">{desc}</p>
    </button>
  );
}

export default function NewMeeting() {
  const { id } = useParams<{ id: string }>();
  const nav = useNavigate();
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [busy, setBusy] = useState(false);

  // paste
  const [notes, setNotes] = useState("");

  // simulate
  const [age, setAge] = useState(50);
  const [situation, setSituation] = useState("");
  const [concerns, setConcerns] = useState("");
  const [risk, setRisk] = useState("moderate");
  const [exchanges, setExchanges] = useState(3);

  // live capture
  const [devices, setDevices] = useState<{ index: number; name: string; channels: number }[]>([]);
  const [device, setDevice] = useState<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [liveMsg, setLiveMsg] = useState("");

  useEffect(() => {
    api.client(id!).then(setClient).catch(() => {});
  }, [id]);

  useEffect(() => {
    if (mode === "live")
      api.audioDevices().then((d) => {
        setDevices(d);
        if (d.length && device == null) setDevice(d[0].index);
      }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  useEffect(() => {
    if (!recording) return;
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  const fmtElapsed = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const startLive = async () => {
    if (device == null) return;
    setLiveMsg("");
    try {
      await api.liveStart(id!, device);
      setElapsed(0);
      setRecording(true);
    } catch (e) {
      setLiveMsg((e as Error).message);
    }
  };

  const stopLive = async () => {
    setBusy(true);
    try {
      const r = await api.liveStop(id!);
      setRecording(false);
      if (r.id) nav(`/c/${id}/m/${r.id}`);
      else {
        setLiveMsg("No speech was captured — check your audio setup below and try again.");
        setBusy(false);
      }
    } catch (e) {
      setLiveMsg((e as Error).message);
      setRecording(false);
      setBusy(false);
    }
  };

  const savePaste = async () => {
    setBusy(true);
    try {
      const { id: mid } = await api.createMeeting(id!, notes.trim());
      nav(`/c/${id}/m/${mid}`);
    } catch {
      setBusy(false);
    }
  };

  const runSimulate = async () => {
    setBusy(true);
    try {
      const { meetingId } = await api.simulate(id!, {
        age,
        situation,
        concerns,
        risk_tolerance: risk,
        num_exchanges: exchanges,
        save: true,
      });
      if (meetingId) nav(`/c/${id}/m/${meetingId}`);
    } catch {
      setBusy(false);
    }
  };

  return (
    <>
      <TopBar current={client ? { id: client.id, name: client.name } : undefined} />
      <Page>
        <div className="mb-8 mt-4">
          <Eyebrow>New meeting</Eyebrow>
          <h1 className="mt-2 font-display text-4xl font-medium tracking-tight text-paper">
            How would you like to begin?
          </h1>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <OptionCard
            title="Paste transcript"
            desc="Drop in notes or a transcript from a real meeting."
            active={mode === "paste"}
            onClick={() => setMode("paste")}
          />
          <OptionCard
            title="Live meeting"
            desc="Capture a Zoom, Meet, or Teams call as it happens."
            active={mode === "live"}
            onClick={() => setMode("live")}
          />
          <OptionCard
            title="Simulated meeting"
            desc="Generate a realistic conversation to work from."
            active={mode === "simulate"}
            onClick={() => setMode("simulate")}
          />
        </div>

        <div className="mt-6">
          {mode === "paste" && (
            <Card className="p-5">
              <TextArea
                label="Meeting notes or transcript"
                rows={12}
                value={notes}
                placeholder="John wants to retire at 60, worried about market volatility, daughter starting college in two years…"
                onChange={(e) => setNotes(e.target.value)}
              />
              <div className="mt-4 flex items-center gap-3">
                <Button variant="primary" disabled={!notes.trim() || busy} onClick={savePaste}>
                  {busy ? "Processing…" : "Process meeting"}
                </Button>
                {busy && <Spinner />}
              </div>
            </Card>
          )}

          {mode === "live" && (
            <Card className="p-6">
              {!recording ? (
                <>
                  <h3 className="font-display text-lg text-paper">Capture a live call</h3>
                  <p className="mt-2 max-w-xl text-sm text-mist">
                    Records this Zoom, Meet, or Teams call through your Mac's audio, then turns it into a
                    meeting. Please let everyone on the call know you're recording.
                  </p>
                  <div className="mt-5 max-w-sm">
                    <span className="mb-1.5 block text-xs font-medium text-mist">Capture device</span>
                    <select
                      value={device ?? ""}
                      onChange={(e) => setDevice(Number(e.target.value))}
                      className="w-full rounded-lg border border-line bg-ink px-3.5 py-2.5 text-sm text-paper focus:border-gilt focus:outline-none"
                    >
                      {devices.map((d) => (
                        <option key={d.index} value={d.index}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="mt-4">
                    <Button variant="primary" disabled={device == null} onClick={startLive}>
                      Start capture
                    </Button>
                  </div>
                  {liveMsg && <p className="mt-3 text-sm text-[#c98b8b]">{liveMsg}</p>}
                  <details className="mt-6 border-t border-line-soft pt-4 text-sm text-mist">
                    <summary className="cursor-pointer text-mute transition-colors hover:text-mist">
                      One-time audio setup
                    </summary>
                    <div className="mt-3 space-y-2 text-sm leading-relaxed text-mist">
                      <p>To capture both sides of a call, route your audio through a free virtual device:</p>
                      <ol className="ml-4 list-decimal space-y-1">
                        <li>
                          Install BlackHole: <code className="text-paper">brew install blackhole-2ch</code>
                        </li>
                        <li>
                          Open <span className="text-paper">Audio MIDI Setup</span>. Create a{" "}
                          <span className="text-paper">Multi-Output Device</span> (your speakers + BlackHole)
                          and set it as your Mac's output so you still hear the call.
                        </li>
                        <li>
                          Create an <span className="text-paper">Aggregate Device</span> (your microphone +
                          BlackHole). Pick that as the capture device above.
                        </li>
                      </ol>
                      <p className="text-mute">
                        First capture will ask macOS for microphone permission — allow it.
                      </p>
                    </div>
                  </details>
                </>
              ) : (
                <div className="flex flex-col items-start gap-4">
                  <div className="flex items-center gap-3">
                    <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#c98b8b]" />
                    <span className="text-sm tabular-nums text-paper">Recording · {fmtElapsed(elapsed)}</span>
                  </div>
                  <p className="max-w-xl text-sm text-mist">
                    Have your call as normal. Stop when you're done and it'll be transcribed and processed.
                  </p>
                  <div className="flex items-center gap-3">
                    <Button variant="primary" disabled={busy} onClick={stopLive}>
                      {busy ? "Processing…" : "Stop and process"}
                    </Button>
                    {busy && <Spinner />}
                  </div>
                </div>
              )}
            </Card>
          )}

          {mode === "simulate" && (
            <Card className="p-5">
              <div className="mb-4 flex flex-wrap gap-2">
                {PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => {
                      setAge(p.age);
                      setSituation(p.situation);
                      setConcerns(p.concerns);
                      setRisk(p.risk);
                    }}
                    className="rounded-full border border-line px-3 py-1.5 text-xs text-mist transition-colors hover:border-gilt/60 hover:text-paper"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field
                  label="Age"
                  type="number"
                  value={age}
                  onChange={(e) => setAge(Number(e.target.value))}
                />
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-mist">Risk tolerance</span>
                  <select
                    value={risk}
                    onChange={(e) => setRisk(e.target.value)}
                    className="w-full rounded-lg border border-line bg-ink px-3.5 py-2.5 text-sm text-paper focus:border-gilt focus:outline-none"
                  >
                    <option value="conservative">Conservative</option>
                    <option value="moderate">Moderate</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                </label>
              </div>
              <div className="mt-4 space-y-4">
                <TextArea
                  label="Situation"
                  rows={2}
                  value={situation}
                  placeholder="Software executive, recently sold equity, spouse is a physician…"
                  onChange={(e) => setSituation(e.target.value)}
                />
                <TextArea
                  label="What's on their mind"
                  rows={2}
                  value={concerns}
                  placeholder="Worried about taxes from the sale, wants to retire by 58…"
                  onChange={(e) => setConcerns(e.target.value)}
                />
              </div>
              <div className="mt-4 flex items-center gap-3">
                <Button
                  variant="primary"
                  disabled={!situation.trim() || !concerns.trim() || busy}
                  onClick={runSimulate}
                >
                  {busy ? "Generating…" : "Generate two-advisor conversation"}
                </Button>
                {busy && <Spinner label="Two AIs are talking, then processing…" />}
              </div>
              <p className="mt-4 border-t border-line-soft pt-3 text-xs text-mute">
                Want to speak it yourself, out loud and interruptible? Launch the live voice room from your
                terminal:{" "}
                <code className="text-mist">
                  WM_LIVE_CLIENT="{client?.name ?? ""}" python3 live/bot.py
                </code>
              </p>
            </Card>
          )}
        </div>
      </Page>
    </>
  );
}
