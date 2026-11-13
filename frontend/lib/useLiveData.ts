import { useCallback, useEffect, useState } from "react";

/**
 * Load data with `fetcher`, expose `reload()`, and keep re-fetching every `ms`
 * while `shouldPoll(data)` is true (e.g. while an episode is still generating).
 * `fetcher` must be stable (wrap it in useCallback).
 */
export function useLiveData<T>(fetcher: () => Promise<T>, shouldPoll: (data: T) => boolean = () => false, ms = 5000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [version, setVersion] = useState(0);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    let cancelled = false;
    fetcher().then(
      (result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      },
      (err) => {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [fetcher, version]);

  const polling = data !== null && shouldPoll(data);
  useEffect(() => {
    if (!polling) return;
    const id = setInterval(reload, ms);
    return () => clearInterval(id);
  }, [polling, reload, ms]);

  return { data, error, reload, setData };
}
