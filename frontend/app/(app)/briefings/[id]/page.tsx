import { Suspense } from "react";
import BriefingView from "@/components/BriefingView";

export default function BriefingPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading…</p>}>
      <BriefingView />
    </Suspense>
  );
}
