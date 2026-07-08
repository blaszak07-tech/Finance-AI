import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api, money } from "../api";
import type { ClientDetail, AgentResult } from "../types";
import { TopBar, Page } from "../Shell";
import { Card, Button, Eyebrow, Spinner, Markdown, Modal, Field, TextArea } from "../ui";

function AskPanel({ id }: { id: string }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AgentResult | null>(null);
  const [showTrace, setShowTrace] = useState(false);

  const ask = async () => {
    if (!q.trim()) return;
    setBusy(true);
    setRes(null);
    try {
      setRes(await api.ask(id, q.trim()));
    } catch (e) {
      setRes({ answer: `Something went wrong: ${(e as Error).message}`, steps: [] });
    }
    setBusy(false);
  };

  return (
    <Card className="p-5">
      <Eyebrow>Ask</Eyebrow>
      <div className="mt-3 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Anything about this client — history, positioning, what to do next"
          className="flex-1 rounded-lg border border-line bg-ink px-3.5 py-2.5 text-sm text-paper placeholder:text-mute focus:border-gilt focus:outline-none"
        />
        <Button variant="primary" onClick={ask} disabled={!q.trim() || busy}>
          Ask
        </Button>
      </div>

      {busy && (
        <div className="mt-4">
          <Spinner label="Searching history, consulting specialists…" />
        </div>
      )}

      {res && (
        <div className="mt-5">
          <Markdown>{res.answer}</Markdown>
          {res.steps.length > 0 && (
            <div className="mt-4 border-t border-line-soft pt-3">
              <button
                onClick={() => setShowTrace((s) => !s)}
                className="text-xs text-mute transition-colors hover:text-mist"
              >
                {showTrace ? "Hide reasoning" : `How it answered · ${res.steps.filter((s) => s.type === "action").length} steps`}
              </button>
              {showTrace && (
                <div className="mt-3 space-y-2">
                  {res.steps.map((s, i) =>
                    s.type === "action" ? (
                      <div key={i} className="text-xs text-mist">
                        <span className="text-gilt">{s.tool}</span>
                        <span className="text-mute"> · {JSON.stringify(s.input)}</span>
                      </div>
                    ) : (
                      <div key={i} className="text-xs italic text-mute">
                        {s.text}
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function ManageMenu({ client, onChange }: { client: ClientDetail; onChange: () => void }) {
  const [mode, setMode] = useState<null | "rename" | "delete">(null);
  const [name, setName] = useState(client.name);
  const nav = useNavigate();

  return (
    <>
      <div className="flex gap-4 text-sm">
        <button className="text-mute transition-colors hover:text-mist" onClick={() => setMode("rename")}>
          Rename
        </button>
        <button className="text-mute transition-colors hover:text-[#c98b8b]" onClick={() => setMode("delete")}>
          Remove
        </button>
      </div>
      {mode === "rename" && (
        <Modal onClose={() => setMode(null)}>
          <h2 className="mb-4 font-display text-xl">Rename client</h2>
          <Field label="Name" value={name} autoFocus onChange={(e) => setName(e.target.value)} />
          <div className="mt-6 flex justify-end gap-2">
            <Button variant="quiet" onClick={() => setMode(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={async () => {
                const updated = await api.renameClient(client.id, name.trim());
                setMode(null);
                if (updated.id !== client.id) nav(`/c/${updated.id}`);
                else onChange();
              }}
            >
              Save
            </Button>
          </div>
        </Modal>
      )}
      {mode === "delete" && (
        <Modal onClose={() => setMode(null)}>
          <h2 className="mb-2 font-display text-xl">Remove {client.name}?</h2>
          <p className="mb-6 text-sm text-mist">
            This permanently deletes the client and all {client.meetings.length} meetings.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="quiet" onClick={() => setMode(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              className="bg-[#c98b8b] hover:bg-[#d8a0a0]"
              onClick={async () => {
                await api.deleteClient(client.id);
                nav("/");
              }}
            >
              Remove
            </Button>
          </div>
        </Modal>
      )}
    </>
  );
}

export default function ClientHome() {
  const { id } = useParams<{ id: string }>();
  const [client, setClient] = useState<ClientDetail | null>(null);
  const nav = useNavigate();

  const load = () => api.client(id!).then(setClient).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!client)
    return (
      <>
        <TopBar />
        <Page>
          <Spinner label="Loading" />
        </Page>
      </>
    );

  const fin = client.financials;

  return (
    <>
      <TopBar current={{ id: client.id, name: client.name }} />
      <Page>
        {/* Hero */}
        <div className="mb-8 mt-4 flex items-end justify-between">
          <div>
            <Eyebrow>Client</Eyebrow>
            <h1 className="mt-2 font-display text-5xl font-medium tracking-tight text-paper">
              {client.name}
            </h1>
            <div className="mt-3 flex items-center gap-4 text-sm text-mist">
              <span>
                {client.meetings.length} {client.meetings.length === 1 ? "meeting" : "meetings"}
              </span>
              {client.netWorth != null && (
                <>
                  <span className="text-mute">·</span>
                  <span className="tabular-nums text-gilt">{money(client.netWorth)} net worth</span>
                </>
              )}
            </div>
          </div>
          <ManageMenu client={client} onChange={load} />
        </div>

        <div className="mb-3 flex justify-end">
          <Button variant="primary" onClick={() => nav(`/c/${client.id}/new`)}>
            New meeting
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left: ask + meetings */}
          <div className="space-y-6 lg:col-span-2">
            <AskPanel id={client.id} />

            <div>
              <Eyebrow>Meetings</Eyebrow>
              <div className="mt-3 space-y-2">
                {client.meetings.length === 0 && (
                  <Card className="p-5 text-sm text-mute">
                    No meetings yet. Start one to build this client's picture.
                  </Card>
                )}
                {client.meetings.map((m) => (
                  <Card key={m.id} onClick={() => nav(`/c/${client.id}/m/${m.id}`)} className="p-4">
                    <div className="text-xs text-mute">{m.timestamp}</div>
                    <div className="mt-1.5 line-clamp-2 text-sm text-mist">
                      {m.summary.replace(/[#*`]/g, "").slice(0, 200)}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {/* Right: snapshot */}
          <div className="space-y-6">
            {fin && (fin.accounts?.length || fin.risk_tolerance) && (
              <Card className="p-5">
                <Eyebrow>Financial snapshot</Eyebrow>
                {client.netWorth != null && (
                  <div className="mt-3 font-display text-3xl tabular-nums text-paper">
                    {money(client.netWorth)}
                  </div>
                )}
                <div className="mt-4 space-y-1.5">
                  {fin.accounts?.map((a, i) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-mist">{a.name}</span>
                      <span className="tabular-nums text-paper">{money(a.balance)}</span>
                    </div>
                  ))}
                </div>
                {fin.risk_tolerance && (
                  <div className="mt-4 border-t border-line-soft pt-3 text-sm">
                    <span className="text-mute">Risk tolerance</span>{" "}
                    <span className="text-mist">{fin.risk_tolerance}</span>
                  </div>
                )}
              </Card>
            )}

            {Object.keys(client.profile).length > 0 && (
              <Card className="p-5">
                <Eyebrow>Known facts</Eyebrow>
                <div className="mt-3 space-y-1.5">
                  {Object.entries(client.profile).map(([k, v]) => (
                    <div key={k} className="text-sm">
                      <span className="text-mute">{k.replace(/_/g, " ")}: </span>
                      <span className="text-mist">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </Page>
    </>
  );
}
