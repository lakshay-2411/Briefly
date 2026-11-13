"use client";

import { useMemo, useState } from "react";
import type { BriefingInput } from "@/lib/api";
import { browserTimezone } from "@/lib/format";

interface Props {
  initial?: BriefingInput;
  submitLabel: string;
  onSubmit: (value: BriefingInput) => Promise<void>;
  onCancel?: () => void;
}

export default function BriefingForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [topic, setTopic] = useState(initial?.topic ?? "");
  const [time, setTime] = useState(initial?.time_of_day.slice(0, 5) ?? "08:00");
  const [timezone, setTimezone] = useState(initial?.timezone ?? browserTimezone());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const timezones = useMemo(() => {
    const all = Intl.supportedValuesOf("timeZone");
    return all.includes(timezone) ? all : [timezone, ...all];
  }, [timezone]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit({ topic: topic.trim(), time_of_day: time, timezone });
      if (!initial) setTopic("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="block">
        <span className="label">What should we research every day?</span>
        <textarea
          required
          minLength={3}
          maxLength={500}
          rows={2}
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Find all startup funding announced in the last 24 hours"
          className="input resize-none"
        />
      </label>

      <div className="grid gap-4 sm:grid-cols-[10rem_1fr]">
        <label className="block">
          <span className="label">Deliver daily at</span>
          <input type="time" required value={time} onChange={(e) => setTime(e.target.value)} className="input" />
        </label>
        <label className="block min-w-0">
          <span className="label">Timezone</span>
          <select value={timezone} onChange={(e) => setTimezone(e.target.value)} className="input">
            {timezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-2">
        <button type="submit" disabled={busy} className="btn-primary">
          {busy ? "Saving…" : submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
