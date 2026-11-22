import { useCallback, useRef, useState } from 'react';
import { ApiError } from '../../lib/api/types';

/**
 * Shared async-request lifecycle for the data hooks (#26): a monotonic
 * generation counter plus loading/error state. `run` guards stale async results
 * after a scope/plant/range change; `reset` invalidates any in-flight request.
 */
export function useRequestState(initialLoading = true, fallbackMessage = 'Unable to load data.') {
  const generation = useRef(0);
  const [loading, setLoading] = useState(initialLoading);
  const [error, setError] = useState<ApiError>();

  const run = useCallback(async (task: () => Promise<void>): Promise<boolean | undefined> => {
    const request = ++generation.current;
    setLoading(true);
    setError(undefined);
    try {
      await task();
      return request === generation.current ? true : undefined;
    } catch (cause) {
      if (request !== generation.current) return undefined;
      setError(cause instanceof ApiError ? cause : new ApiError('http', fallbackMessage));
      return false;
    } finally {
      if (request === generation.current) setLoading(false);
    }
  }, [fallbackMessage]);

  /** Invalidate any in-flight request and reset loading/error for a new load. */
  const reset = useCallback((nextLoading: boolean) => {
    generation.current += 1;
    setLoading(nextLoading);
    setError(undefined);
  }, []);

  return { loading, error, run, reset, setLoading };
}