"use client";

import Link from "next/link";
import { useState } from "react";
import { api, type Briefing } from "@/lib/api";
import { formatTime } from "@/lib/format";

interface Props {
  briefing: Briefing;
  generating: boolean;
  onChanged: () => void;
}

export default function BriefingCard({ briefing, generating, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null);

  async function act(fn: () => Promise<unknown>, success?: string) {
    setBusy(true);
    setMessage(null);
    try {
      await fn();
      if (success) setMessage({ text: success });
      onChanged();
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "Something went wrong", error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <Link href={`/briefings/${briefing.id}`} className="min-w-0 hover:underline">
          <p className="font-medium leading-snug">{briefing.topic}</p>
        </Link>
        <label className="flex shrink-0 cursor-pointer items-center gap-2 text-sm text-zinc-600">
          <input
            type="checkbox"
            checked={briefing.is_active}
            disabled={busy}
            onChange={(e) => act(() => api.updateBriefing(briefing.id, { is_active: e.target.checked }))}
            className="h-4 w-4 accent-zinc-900"
          />
          Active
        </label>
      </div>

      <p className="mt-1 text-sm text-zinc-500">
        {briefing.is_active ? "Every day at " : "Paused · "}
        {formatTime(briefing.time_of_day)} · {briefing.timezone.replaceAll("_", " ")}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          disabled={busy || generating}
          onClick={() =>
            act(
              () => api.runBriefing(briefing.id),
              "Generating now. This takes a few minutes and you'll get an email when it's ready.",
            )
          }
          className="btn-primary"
        >
          {generating ? "Generating…" : "Generate now"}
        </button>
        <Link href={`/briefings/${briefing.id}`} className="btn-secondary">
          Edit & episodes
        </Link>
        <button
          disabled={busy}
          onClick={() => {
            if (confirm("Delete this briefing and all its episodes?")) act(() => api.deleteBriefing(briefing.id));
          }}
          className="btn-ghost text-red-600 hover:bg-red-50"
        >
          Delete
        </button>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.error ? "text-red-600" : "text-zinc-600"}`}>{message.text}</p>
      )}
    </div>
  );
}
