import type { EpisodeStatus } from "@/lib/api";
import { formatClock } from "@/lib/format";

const STYLES: Record<EpisodeStatus, { label: string; className: string }> = {
  researching: { label: "Researching", className: "bg-amber-50 text-amber-700 ring-amber-200" },
  writing: { label: "Writing script", className: "bg-amber-50 text-amber-700 ring-amber-200" },
  synthesizing: { label: "Recording audio", className: "bg-amber-50 text-amber-700 ring-amber-200" },
  scheduled: { label: "Scheduled", className: "bg-sky-50 text-sky-700 ring-sky-200" },
  ready: { label: "Ready", className: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  failed: { label: "Failed", className: "bg-red-50 text-red-700 ring-red-200" },
};

export default function StatusBadge({ status, deliverAt }: { status: EpisodeStatus; deliverAt?: string }) {
  const { className } = STYLES[status];
  const label = status === "scheduled" && deliverAt ? `Arrives at ${formatClock(deliverAt)}` : STYLES[status].label;
  const working = status !== "ready" && status !== "failed" && status !== "scheduled";
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${className}`}
    >
      {working && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {label}
    </span>
  );
}
