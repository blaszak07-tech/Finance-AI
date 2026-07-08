import type { ClientSummary, ClientDetail, Meeting, AgentResult, PanelResult } from "./types";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) {
    let detail = r.statusText;
    try {
      detail = (await r.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return r.json();
}

const post = (url: string, body?: unknown) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

export const api = {
  clients: () => fetch("/api/clients").then(j<ClientSummary[]>),
  createClient: (name: string) => post("/api/clients", { name }).then(j<ClientSummary>),
  client: (id: string) => fetch(`/api/clients/${id}`).then(j<ClientDetail>),
  renameClient: (id: string, name: string) =>
    fetch(`/api/clients/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }).then(j<ClientSummary>),
  deleteClient: (id: string) => fetch(`/api/clients/${id}`, { method: "DELETE" }).then(j),

  quicklook: (id: string) => fetch(`/api/clients/${id}/quicklook`).then(j<{ markdown: string }>),
  meeting: (id: string, mid: string) => fetch(`/api/clients/${id}/meetings/${mid}`).then(j<Meeting>),
  createMeeting: (id: string, notes: string) =>
    post(`/api/clients/${id}/meetings`, { notes }).then(j<{ id: string }>),
  analyze: (id: string, mid: string) =>
    post(`/api/clients/${id}/meetings/${mid}/analyze`).then(j<PanelResult>),

  ask: (id: string, question: string) => post(`/api/clients/${id}/ask`, { question }).then(j<AgentResult>),

  simulate: (id: string, body: Record<string, unknown>) =>
    post(`/api/clients/${id}/simulate`, body).then(j<{ meetingId: string | null; transcript: string }>),
};

export const money = (n: number | null | undefined) =>
  n == null ? null : n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
