/**
 * Pure Fetch-Metadata rule shared by `assertSameSiteRequest` (server functions)
 * and the raw `/api/act` and `/api/complete` routes. No framework import, so the
 * route handlers and their `node:test` suites can load it directly.
 */
export function isCrossSiteScripted(request: Request): boolean {
  const h = request.headers;
  const site = h.get("sec-fetch-site");
  // Non-browser client (no header), the app's own origin, or a direct
  // (address-bar/bookmark) load are all fine.
  if (!site || site === "same-origin" || site === "none") return false;
  // A top-level GET navigation (e.g. the broker's OAuth callback redirect) is
  // fine even when it's cross-site; scripted requests never set navigate mode.
  const dest = h.get("sec-fetch-dest");
  const isTopLevelGet =
    h.get("sec-fetch-mode") === "navigate" &&
    request.method === "GET" &&
    dest !== "object" &&
    dest !== "embed";
  return !isTopLevelGet;
}

/**
 * 403 for a scripted cross-site/sibling request, 415 for a non-JSON body (a
 * `text/plain` POST is a CORS simple request and skips preflight), else null.
 */
export function rejectUnsafeJsonPost(request: Request): Response | null {
  if (isCrossSiteScripted(request))
    return Response.json({ ok: false, error: "cross-site request blocked" }, { status: 403 });
  const type = (request.headers.get("content-type") ?? "").toLowerCase();
  if (!type.startsWith("application/json"))
    return Response.json(
      { ok: false, error: "content-type must be application/json" },
      { status: 415 },
    );
  return null;
}
