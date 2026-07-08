import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "./api";
import type { ClientSummary } from "./types";
import { Modal, Field, Button } from "./ui";

function Wordmark() {
  return (
    <Link to="/" className="font-display text-lg tracking-tight text-paper">
      Meridian
    </Link>
  );
}

export function AddClientModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (c: ClientSummary) => void;
}) {
  const [name, setName] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setErr("");
    try {
      onCreated(await api.createClient(name.trim()));
    } catch (e) {
      setErr((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <Modal onClose={onClose}>
      <h2 className="mb-1 font-display text-xl">New client</h2>
      <p className="mb-5 text-sm text-mist">Everything else builds from your meetings.</p>
      <Field
        label="Full name"
        autoFocus
        value={name}
        placeholder="e.g. John Smith"
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
      />
      {err && <p className="mt-3 text-sm text-[#c98b8b]">{err}</p>}
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="quiet" onClick={onClose}>
          Cancel
        </Button>
        <Button variant="primary" disabled={!name.trim() || busy} onClick={submit}>
          {busy ? "Adding…" : "Add client"}
        </Button>
      </div>
    </Modal>
  );
}

function ClientSwitcher({ current }: { current: { id: string; name: string } }) {
  const [open, setOpen] = useState(false);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [adding, setAdding] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const nav = useNavigate();

  useEffect(() => {
    if (open) api.clients().then(setClients).catch(() => {});
  }, [open]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 text-sm text-paper transition-colors hover:border-gilt/60"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-gilt" />
        {current.name}
        <span className="text-mute">⌄</span>
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-40 w-60 overflow-hidden rounded-xl border border-line bg-surface shadow-2xl">
          <div className="max-h-72 overflow-y-auto py-1">
            {clients.map((c) => (
              <button
                key={c.id}
                onClick={() => {
                  setOpen(false);
                  nav(`/c/${c.id}`);
                }}
                className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm transition-colors hover:bg-raised ${
                  c.id === current.id ? "text-gilt" : "text-paper"
                }`}
              >
                {c.name}
                <span className="text-xs text-mute">{c.meetingCount || ""}</span>
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              setOpen(false);
              setAdding(true);
            }}
            className="w-full border-t border-line px-4 py-2.5 text-left text-sm text-mist transition-colors hover:bg-raised hover:text-paper"
          >
            New client
          </button>
        </div>
      )}
      {adding && (
        <AddClientModal onClose={() => setAdding(false)} onCreated={(c) => nav(`/c/${c.id}`)} />
      )}
    </div>
  );
}

export function TopBar({ current }: { current?: { id: string; name: string } }) {
  return (
    <header className="relative z-10 mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
      <Wordmark />
      {current && <ClientSwitcher current={current} />}
    </header>
  );
}

export function Page({ children }: { children: React.ReactNode }) {
  return <main className="relative z-10 mx-auto max-w-5xl px-6 pb-24">{children}</main>;
}
