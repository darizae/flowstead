/**
 * Typed UTC-timestamp parsing for the domain (#70). API strings are converted
 * to `Date` exactly once at the transform boundary; downstream chart code
 * consumes `Date` and never re-parses ISO strings.
 */

/** Parse a UTC timestamp, throwing a descriptive error on invalid input. */
export function parseUtcTimestamp(value: string, what: string): Date {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) throw new RangeError(`Invalid ${what}: ${value}`);
  return date;
}

/** Parse a UTC timestamp, returning null when it is not a valid date. */
export function tryParseUtc(value: string): Date | null {
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date : null;
}