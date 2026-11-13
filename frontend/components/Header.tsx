"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function Header() {
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setEmail(data.session?.user.email ?? null));
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span>🎧</span> Daily Briefing
        </Link>
        <div className="flex min-w-0 items-center gap-4 text-sm">
          {email && <span className="hidden truncate text-zinc-500 sm:inline">{email}</span>}
          <button onClick={signOut} className="text-zinc-600 hover:text-zinc-900">
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
