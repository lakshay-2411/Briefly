"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import StatusBadge from "@/components/StatusBadge";
import { api, ApiError, IN_PROGRESS, type EpisodeDetail } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/format";
import { useLiveData } from "@/lib/useLiveData";

const isGenerating = (e: EpisodeDetail) => IN_PROGRESS.includes(e.status);

export default function EpisodeView() {
  const { id } = useParams<{ id: string }>();
  const fetcher = useCallback(() => api.getEpisode(id), [id]);
  const { data: episode, error } = useLiveData(fetcher, isGenerating);

  if (error) {
    const notFound = error instanceof ApiError && error.status === 404;
    return <p className="text-sm text-red-600">{notFound ? "Episode not found." : error.message}</p>;
  }
  if (!episode) return <p className="text-sm text-zinc-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <Link href={`/briefings/${episode.briefing_id}`} className="text-sm text-zinc-500 hover:text-zinc-900">
        ← {episode.topic}
      </Link>

      <section className="card p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-xl font-semibold leading-snug tracking-tight">
              {episode.title ?? "Generating your episode…"}
            </h1>
            <p className="mt-1 text-sm text-zinc-500">
              {formatDateTime(episode.created_at)}
              {episode.duration_seconds ? ` · ${formatDuration(episode.duration_seconds)}` : ""}
            </p>
          </div>
          <StatusBadge status={episode.status} />
        </div>

        {episode.audio_url && (
          <audio controls preload="metadata" src={episode.audio_url} className="mt-5 w-full" />
        )}

        {isGenerating(episode) && (
          <p className="mt-4 text-sm text-zinc-500">
            The agent is working on this episode. This page updates automatically, and you&apos;ll also get an
            email when it&apos;s ready.
          </p>
        )}
        {episode.status === "failed" && (
          <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            This episode couldn&apos;t be generated{episode.error ? `: ${episode.error}` : "."}
          </p>
        )}
        {episode.summary && <p className="mt-5 leading-relaxed text-zinc-700">{episode.summary}</p>}
      </section>

      {episode.sources && episode.sources.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold tracking-tight">Sources</h2>
          <ul className="card divide-y divide-zinc-100">
            {episode.sources.map((s) => (
              <li key={s.url} className="p-4">
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
                  {s.title}
                </a>
                <p className="truncate text-sm text-zinc-500">{new URL(s.url).hostname.replace(/^www\./, "")}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {episode.script && (
        <details className="card p-5">
          <summary className="cursor-pointer font-medium">Read the transcript</summary>
          <div className="mt-4 whitespace-pre-line leading-relaxed text-zinc-700">{episode.script}</div>
        </details>
      )}
    </div>
  );
}
