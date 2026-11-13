import { createBrowserClient } from "@supabase/ssr";

// Session lives in cookies so proxy.ts can see it on the server.
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);
