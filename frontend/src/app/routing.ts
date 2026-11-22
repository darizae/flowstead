/**
 * Minimal path-based routing for the app. Only `/plants` and `/plants/:id` exist
 * today, so this stays a tiny helper rather than a routing dependency (#28).
 */

export function plantIdFromLocation(): string | undefined {
  const match = window.location.pathname.match(/^\/plants\/([^/]+)\/?$/);
  if (!match) return undefined;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return "";
  }
}

export function navigate(path: string): void {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
