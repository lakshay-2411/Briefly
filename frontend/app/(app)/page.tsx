"use client";

import { useCallback } from "react";
import BriefingCard from "@/components/BriefingCard";
import BriefingForm from "@/components/BriefingForm";
import EpisodeList from "@/components/EpisodeList";
import { api, IN_PROGRESS, PENDING, type EpisodeSummary } from "@/lib/api";
import { useLiveData } from "@/lib/useLiveData";

const anyPending = (d: { episodes: EpisodeSummary[] }) => d.episodes.some((e) => PENDING.includes(e.status));

export default function Dashboard() {
  const fetcher = useCallback(async () => {
    const [briefings, episodes] = await Promise.all([api.listBriefings(), api.listEpisodes()]);
    return { briefings, episodes };
  }, []);
  const { data, error, reload } = useLiveData(fetcher, anyPending);

  const generatingIds = new Set(
    (data?.episodes ?? []).filter((e) => IN_PROGRESS.includes(e.status)).map((e) => e.briefing_id),
  );

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-semibold tracking-tight">New briefing</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Pick a topic and a time. Every day an agent researches the latest news on it and emails you a
          five-minute audio episode.
        </p>
        <div className="card mt-4 p-5">
          <BriefingForm
            submitLabel="Create briefing"
            onSubmit={async (value) => {
              await api.createBriefing(value);
              reload();
            }}
          />
        </div>
      </section>

      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error.message}</p>}

      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Your briefings</h2>
        {data === null ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : data.briefings.length === 0 ? (
          <p className="card p-6 text-center text-sm text-zinc-500">No briefings yet. Create one above.</p>
        ) : (
          <div className="space-y-3">
            {data.briefings.map((b) => (
              <BriefingCard key={b.id} briefing={b} generating={generatingIds.has(b.id)} onChanged={reload} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Recent episodes</h2>
        <EpisodeList
          episodes={data?.episodes ?? []}
          emptyText="Episodes will appear here once they're generated."
        />
      </section>
    </div>
  );
}
