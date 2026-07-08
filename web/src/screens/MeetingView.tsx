import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Meeting, PanelResult } from "../types";
import { TopBar, Page } from "../Shell";
import { Card, Button, Eyebrow, Spinner, Markdown } from "../ui";

const TABS = [
  ["summary", "Summary"],
  ["action_items", "Action items"],
  ["flags", "Planning flags"],
  ["email", "Follow-up"],
  ["notes", "Transcript"],
] as const;

type TabKey = (typeof TABS)[number][0];

function Analysis({ id, mid }: { id: string; mid: string }) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<PanelResult | null>(null);

  const run = async () => {
    setBusy(true);
    try {
      setRes(await api.analyze(id, mid));
    } finally {
      setBusy(false);
    }
  };

  if (!res)
    return (
      <Card className="p-6">
        <Eyebrow>Specialist analysis</Eyebrow>
        <p className="mt-2 max-w-xl text-sm text-mist">
          Route this meeting to the relevant specialists — retirement, tax, portfolio risk — who review
          it, respond to each other, and hand up a single prioritized plan.
        </p>
        <div className="mt-4 flex items-center gap-3">
          <Button variant="primary" onClick={run} disabled={busy}>
            {busy ? "Convening…" : "Analyze"}
          </Button>
          {busy && <Spinner label="Specialists reviewing & conferring…" />}
        </div>
      </Card>
    );

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <Eyebrow>Recommended plan</Eyebrow>
        <div className="mt-3">
          <Markdown>{res.synthesis}</Markdown>
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {res.round1.map((f) => {
          const cross = res.cross.find((c) => c.key === f.key);
          return (
            <Card key={f.key} className="p-5">
              <div className="text-sm font-medium text-gilt">{f.label}</div>
              <div className="mt-2">
                <Markdown>{f.text}</Markdown>
              </div>
              {cross && (
                <div className="mt-3 border-t border-line-soft pt-3">
                  <div className="text-xs uppercase tracking-wider text-mute">On the others</div>
                  <div className="mt-1">
                    <Markdown>{cross.text}</Markdown>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}

export default function MeetingView() {
  const { id, mid } = useParams<{ id: string; mid: string }>();
  const nav = useNavigate();
  const [m, setM] = useState<Meeting | null>(null);
  const [tab, setTab] = useState<TabKey>("summary");
  const [showAnalysis, setShowAnalysis] = useState(false);

  useEffect(() => {
    api.meeting(id!, mid!).then(setM).catch(() => {});
  }, [id, mid]);

  if (!m)
    return (
      <>
        <TopBar />
        <Page>
          <Spinner label="Loading" />
        </Page>
      </>
    );

  return (
    <>
      <TopBar />
      <Page>
        <button
          onClick={() => nav(`/c/${id}`)}
          className="mb-6 mt-2 text-sm text-mute transition-colors hover:text-mist"
        >
          ← Back to client
        </button>

        <div className="mb-6 flex items-end justify-between">
          <div>
            <Eyebrow>Meeting</Eyebrow>
            <h1 className="mt-2 font-display text-3xl font-medium tracking-tight text-paper">
              {m._timestamp}
            </h1>
          </div>
          <Button variant="ghost" onClick={() => setShowAnalysis((s) => !s)}>
            {showAnalysis ? "Hide analysis" : "Analyze"}
          </Button>
        </div>

        {showAnalysis && (
          <div className="mb-8">
            <Analysis id={id!} mid={mid!} />
          </div>
        )}

        <div className="mb-5 flex flex-wrap gap-1 border-b border-line">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`-mb-px border-b-2 px-4 py-2.5 text-sm transition-colors ${
                tab === key
                  ? "border-gilt text-paper"
                  : "border-transparent text-mist hover:text-paper"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <Card className="p-6">
          {tab === "notes" ? (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-mist">
              {m.notes}
            </pre>
          ) : (
            <Markdown>{m[tab] || "—"}</Markdown>
          )}
        </Card>
      </Page>
    </>
  );
}
