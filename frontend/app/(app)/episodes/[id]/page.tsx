import { Suspense } from "react";
import EpisodeView from "@/components/EpisodeView";

export default function EpisodePage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading…</p>}>
      <EpisodeView />
    </Suspense>
  );
}
