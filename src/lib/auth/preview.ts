/**
 * Shared LIVE-PREVIEW OAuth client (server-only — NEVER import from the client).
 *
 * The sandbox serves each live preview on a dynamic `https://*.grok-sandbox.com`
 * URL, which can't be pre-registered per app. The broker instead exposes ONE
 * shared "preview" client. This package emits
 * `https://*.grok-sandbox.com/api/auth/callback/*`.
 * `app-builder-deployer/auth/src/preview-oauth.ts` was written for the previous
 * `oauth2/callback` allowlist; live admission of the 1.7 callback is not proven
 * here. The preview client id is listed here. The client secret must come from
 * `GROK_AUTH_CLIENT_SECRET` in the environment and is never baked into the
 * source. When deployed the deployer injects a per-app `GROK_AUTH_*`
 * (see `server.ts`).
 *
 * The preview client id is `grok_preview`. The matching client secret must
 * be provided as `GROK_AUTH_CLIENT_SECRET` in the environment (the broker
 * stores only the secret's `base64url(SHA-256)` hash). This is a dedicated,
 * low-privilege client (preview-only, `*.grok-sandbox.com`). Rotate it by
 * regenerating the broker env var and updating every consumer's environment.
 */
export const PREVIEW_CLIENT_ID = "grok_preview";

/** The shared auth broker issuer (OIDC discovery lives under it). */
export const GROK_ISSUER_DEFAULT = "https://auth.grok.me";

/**
 * Host patterns whose callbacks the preview client accepts. Better Auth derives
 * the live preview's real origin from the request host and validates it against
 * this list (wildcard-matched), so the OAuth `redirect_uri` becomes the concrete
 * `https://<preview-host>/api/auth/callback/<providerId>` that Better Auth 1.7 emits.
 * Live broker registration of that callback is outside this package.
 */
export const PREVIEW_ALLOWED_HOSTS = ["*.grok-sandbox.com"] as const;
