"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useState } from "react";
import BriefingForm from "@/components/BriefingForm";
import EpisodeList from "@/components/EpisodeList";
import { api, ApiError, IN_PROGRESS, PENDING, type Briefing, type EpisodeSummary } from "@/lib/api";
import { formatTime } from "@/lib/format";
import { useLiveData } from "@/lib/useLiveData";

type Data = { briefing: Briefing; episodes: EpisodeSummary[] };
const anyGenerating = (d: Data) => d.episodes.some((e) => IN_PROGRESS.includes(e.status));
const anyPending = (d: Data) => d.episodes.some((e) => PENDING.includes(e.status));

export default function BriefingView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const fetcher = useCallback(async () => {
    const [briefing, episodes] = await Promise.all([api.getBriefing(id), api.listEpisodes(id)]);
    return { briefing, episodes };
  }, [id]);
  const { data, error, reload, setData } = useLiveData<Data>(fetcher, anyPending);

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return <p className="text-sm text-red-600">{notFound ? "Briefing not found." : error.message}</p>;
  }
  if (!data) return <p className="text-sm text-zinc-500">Loading…</p>;

  const { briefing, episodes } = data;
  const generating = anyGenerating(data);
  const setBriefing = (b: Briefing) => setData({ ...data, briefing: b });

  async function run() {
    setMessage(null);
    try {
      await api.runBriefing(id);
      setMessage("Generating now. This takes a few minutes and you'll get an email when it's ready.");
      reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not start generation");
    }
  }

  async function remove() {
    if (!confirm("Delete this briefing and all its episodes?")) return;
    await api.deleteBriefing(id);
    router.replace("/");
  }

  return (
    <div className="space-y-8">
      <Link href="/" className="text-sm text-zinc-500 hover:text-zinc-900">
        ← All briefings
      </Link>

      <section className="card p-5">
        {editing ? (
          <BriefingForm
            initial={{ topic: briefing.topic, time_of_day: briefing.time_of_day, timezone: briefing.timezone }}
            submitLabel="Save changes"
            onCancel={() => setEditing(false)}
            onSubmit={async (value) => {
              setBriefing(await api.updateBriefing(id, value));
              setEditing(false);
            }}
          />
        ) : (
          <>
            <h1 className="text-xl font-semibold leading-snug tracking-tight">{briefing.topic}</h1>
            <p className="mt-1 text-sm text-zinc-500">
              {briefing.is_active ? "Every day at " : "Paused · "}
              {formatTime(briefing.time_of_day)} · {briefing.timezone.replaceAll("_", " ")}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button onClick={run} disabled={generating} className="btn-primary">
                {generating ? "Generating…" : "Generate now"}
              </button>
              <button onClick={() => setEditing(true)} className="btn-secondary">
                Edit
              </button>
              <button
                onClick={async () => setBriefing(await api.updateBriefing(id, { is_active: !briefing.is_active }))}
                className="btn-secondary"
              >
                {briefing.is_active ? "Pause" : "Resume"}
              </button>
              <button onClick={remove} className="btn-ghost text-red-600 hover:bg-red-50">
                Delete
              </button>
            </div>
            {message && <p className="mt-3 text-sm text-zinc-600">{message}</p>}
          </>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Episodes</h2>
        <EpisodeList
          episodes={episodes}
          showTopic={false}
          emptyText="No episodes yet. Use “Generate now” or wait for the next scheduled run."
        />
      </section>
    </div>
  );
}
