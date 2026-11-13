import { supabase } from "./supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export type EpisodeStatus = "researching" | "writing" | "synthesizing" | "ready" | "failed";

export interface Briefing {
  id: string;
  topic: string;
  time_of_day: string; // "HH:MM:SS"
  timezone: string;
  is_active: boolean;
  next_run_at: string;
  created_at: string;
}

export interface BriefingInput {
  topic: string;
  time_of_day: string; // "HH:MM"
  timezone: string;
}

export interface EpisodeSummary {
  id: string;
  briefing_id: string;
  topic: string;
  status: EpisodeStatus;
  title: string | null;
  summary: string | null;
  duration_seconds: number | null;
  error: string | null;
  created_at: string;
}

export interface EpisodeDetail extends EpisodeSummary {
  script: string | null;
  sources: { title: string; url: string }[] | null;
  audio_url: string | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function toLogin(): never {
  // Plain module code (no router available): a full page load to the login page is intended.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
  throw new ApiError(401, "Not signed in");
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) toLogin();

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init.headers,
    },
  });

  if (res.status === 401) {
    await supabase.auth.signOut();
    toLogin();
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : null;
    throw new ApiError(res.status, message ?? `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  listBriefings: () => request<Briefing[]>("/briefings"),
  getBriefing: (id: string) => request<Briefing>(`/briefings/${id}`),
  createBriefing: (body: BriefingInput) =>
    request<Briefing>("/briefings", { method: "POST", body: JSON.stringify(body) }),
  updateBriefing: (id: string, body: Partial<BriefingInput> & { is_active?: boolean }) =>
    request<Briefing>(`/briefings/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteBriefing: (id: string) => request<void>(`/briefings/${id}`, { method: "DELETE" }),
  runBriefing: (id: string) =>
    request<{ episode_id: string; status: EpisodeStatus }>(`/briefings/${id}/run`, { method: "POST" }),
  listEpisodes: (briefingId?: string) =>
    request<EpisodeSummary[]>(briefingId ? `/episodes?briefing_id=${briefingId}` : "/episodes"),
  getEpisode: (id: string) => request<EpisodeDetail>(`/episodes/${id}`),
};

export const IN_PROGRESS: EpisodeStatus[] = ["researching", "writing", "synthesizing"];
