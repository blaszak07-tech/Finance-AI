import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { ClientSummary } from "../types";
import { TopBar, Page, AddClientModal } from "../Shell";
import { Card, Spinner } from "../ui";

export default function Landing() {
  const [clients, setClients] = useState<ClientSummary[] | null>(null);
  const [adding, setAdding] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    api.clients().then(setClients).catch(() => setClients([]));
  }, []);

  return (
    <>
      <TopBar />
      <Page>
        <div className="mb-10 mt-6">
          <h1 className="font-display text-4xl font-medium tracking-tight text-paper">Clients</h1>
        </div>

        {clients === null ? (
          <Spinner label="Loading" />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {clients.map((c) => (
              <Card key={c.id} onClick={() => nav(`/c/${c.id}`)} className="p-5">
                <div className="font-display text-xl text-paper">{c.name}</div>
                <div className="mt-4 text-sm text-mist">
                  {c.meetingCount} {c.meetingCount === 1 ? "meeting" : "meetings"}
                </div>
                {c.lastMeeting && (
                  <div className="mt-1 text-xs text-mute">Last seen {c.lastMeeting}</div>
                )}
              </Card>
            ))}

            <button
              onClick={() => setAdding(true)}
              className="flex min-h-[7.5rem] items-center justify-center rounded-xl border border-dashed border-line text-sm text-mist transition-colors hover:border-gilt/60 hover:text-paper"
            >
              New client
            </button>
          </div>
        )}

        {clients?.length === 0 && (
          <p className="mt-6 text-sm text-mute">Add your first client to begin.</p>
        )}
      </Page>

      {adding && <AddClientModal onClose={() => setAdding(false)} onCreated={(c) => nav(`/c/${c.id}`)} />}
    </>
  );
}
