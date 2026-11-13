import Link from "next/link";
import type { EpisodeSummary } from "@/lib/api";
import { formatDateTime, formatDuration } from "@/lib/format";
import StatusBadge from "./StatusBadge";

export default function EpisodeList({
  episodes,
  showTopic = true,
  emptyText = "No episodes yet.",
}: {
  episodes: EpisodeSummary[];
  showTopic?: boolean;
  emptyText?: string;
}) {
  if (episodes.length === 0) {
    return <p className="card p-6 text-center text-sm text-zinc-500">{emptyText}</p>;
  }

  return (
    <ul className="card divide-y divide-zinc-100">
      {episodes.map((ep) => (
        <li key={ep.id}>
          <Link href={`/episodes/${ep.id}`} className="flex items-start justify-between gap-4 p-4 hover:bg-zinc-50">
            <div className="min-w-0">
              <p className="truncate font-medium">{ep.title ?? (ep.status === "failed" ? "Episode failed" : "Generating episode…")}</p>
              <p className="mt-0.5 truncate text-sm text-zinc-500">
                {formatDateTime(ep.created_at)}
                {ep.duration_seconds ? ` · ${formatDuration(ep.duration_seconds)}` : ""}
                {showTopic ? ` · ${ep.topic}` : ""}
              </p>
            </div>
            <StatusBadge status={ep.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
