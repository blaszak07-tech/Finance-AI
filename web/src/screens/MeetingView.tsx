import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Meeting } from "../types";
import { TopBar, Page } from "../Shell";
import { Card, Eyebrow, Spinner, Markdown } from "../ui";

const TABS = [
  ["summary", "Summary"],
  ["action_items", "Action items"],
  ["flags", "Planning flags"],
  ["notes", "Transcript"],
] as const;

type TabKey = (typeof TABS)[number][0];

function Transcript({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  const isDialog = blocks.some((b) => /^[A-Z][a-zA-Z]+\s*:/.test(b));

  if (!isDialog)
    return <p className="whitespace-pre-wrap text-sm leading-relaxed text-mist">{text}</p>;

  return (
    <div className="space-y-5">
      {blocks.map((b, i) => {
        const m = b.match(/^([A-Za-z][A-Za-z ]+?)\s*:\s*([\s\S]*)$/);
        if (!m) return <p key={i} className="text-sm text-mist">{b}</p>;
        return (
          <div key={i}>
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-gilt">{m[1]}</div>
            <p className="mt-1 text-sm leading-relaxed text-mist">{m[2]}</p>
          </div>
        );
      })}
    </div>
  );
}

export default function MeetingView() {
  const { id, mid } = useParams<{ id: string; mid: string }>();
  const nav = useNavigate();
  const [m, setM] = useState<Meeting | null>(null);
  const [tab, setTab] = useState<TabKey>("summary");

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

        <div className="mb-6">
          <Eyebrow>Meeting</Eyebrow>
          <h1 className="mt-2 font-display text-3xl font-medium tracking-tight text-paper">
            {m._timestamp}
          </h1>
        </div>

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
          {tab === "notes" ? <Transcript text={m.notes} /> : <Markdown>{m[tab] || "—"}</Markdown>}
        </Card>
      </Page>
    </>
  );
}
