import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createAuthClient } from "better-auth/client";
import { betterAuth } from "better-auth";
import { memoryAdapter } from "better-auth/adapters/memory";
import { genericOAuth } from "better-auth/plugins";

const origin = "https://app.example.invalid";

test("the installed client sends generic provider sign-in through the social API", async () => {
  const requests = [];
  const client = createAuthClient({
    baseURL: origin,
    fetchOptions: {
      customFetchImpl: async (url, init) => {
        requests.push({ url: String(url), method: init.method, body: JSON.parse(init.body) });
        return Response.json({ url: "https://broker.example.invalid/authorize", redirect: true });
      },
    },
  });
  const result = await client.signIn.social({
    provider: "offline-broker",
    callbackURL: "/",
    errorCallbackURL: "/?error=1",
  });
  assert.equal(result.error, null);
  assert.equal(result.data.url, "https://broker.example.invalid/authorize");
  assert.deepEqual(requests, [
    {
      url: `${origin}/api/auth/sign-in/social`,
      method: "POST",
      body: { provider: "offline-broker", callbackURL: "/", errorCallbackURL: "/?error=1" },
    },
  ]);
});

test("the installed server initializes a generic provider without contacting it", async (t) => {
  t.mock.method(globalThis, "fetch", () => {
    throw new Error("network forbidden");
  });
  const auth = betterAuth({
    baseURL: origin,
    secret: "synthetic-offline-compatibility-secret-never-production",
    database: memoryAdapter({}),
    plugins: [
      genericOAuth({
        config: [
          {
            providerId: "offline-broker",
            clientId: "synthetic-client",
            clientSecret: "synthetic-secret",
            authorizationUrl: "https://broker.example.invalid/authorize",
            tokenUrl: "https://broker.example.invalid/token",
            userInfoUrl: "https://broker.example.invalid/userinfo",
            scopes: ["profile"],
          },
        ],
      }),
    ],
  });
  const response = await auth.api.signInSocial({
    body: {
      provider: "offline-broker",
      callbackURL: `${origin}/auth/popup?done=1`,
      errorCallbackURL: `${origin}/auth/popup?done=1&error=1`,
    },
    headers: new Headers({ origin }),
    asResponse: true,
  });
  assert.equal(response.status, 200);
  const result = await response.json();
  const authorization = new URL(result.url);
  assert.equal(authorization.origin, "https://broker.example.invalid");
  assert.equal(
    authorization.searchParams.get("redirect_uri"),
    `${origin}/api/auth/callback/offline-broker`,
  );
  assert.equal(authorization.searchParams.get("client_id"), "synthetic-client");
  assert.ok(authorization.searchParams.get("state"));
  assert.ok(authorization.searchParams.get("code_challenge"));
  assert.ok(response.headers.getSetCookie().length);
});

function source(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

test("registered grok providers start through signIn.social with the broker idp", async (t) => {
  const providers = source("src/lib/auth/providers.ts");
  const server = source("src/lib/auth/server.ts");
  const client = source("src/lib/auth/client.ts");
  const popup = source("src/lib/auth/popup.server.ts");
  const table = providers.slice(providers.indexOf("export const GROK_PROVIDERS"));
  const pairs = [...table.matchAll(/providerId: "([^"]+)", idp: "([^"]+)"/g)].map((match) => ({
    providerId: match[1],
    idp: match[2],
  }));
  assert.deepEqual(pairs, [
    { providerId: "grok-google", idp: "google" },
    { providerId: "grok-x", idp: "twitter" },
  ]);
  assert.match(server, /genericOAuth\(\{/);
  assert.match(server, /authorizationUrlParams: \{ idp, prompt: "login" \}/);
  assert.match(server, /authorizationUrl: grokAuthorizationUrl/);
  assert.match(client, /authClient\.signIn\.social\(\{/);
  assert.match(client, /provider: providerId/);
  assert.match(popup, /auth\.api\.signInSocial\(\{/);
  assert.match(popup, /provider: providerId/);
  assert.doesNotMatch(`${client}\n${popup}`, /signIn\.oauth2|genericOAuthClient|signInWithOAuth2/);

  const fetchCalls = [];
  t.mock.method(globalThis, "fetch", (...args) => {
    fetchCalls.push(args);
    throw new Error("network forbidden");
  });
  const issuer = "https://broker.example.invalid";
  const auth = betterAuth({
    baseURL: origin,
    secret: "synthetic-offline-compatibility-secret-never-production",
    database: memoryAdapter({}),
    plugins: [
      genericOAuth({
        config: pairs.map(({ providerId, idp }) => ({
          providerId,
          clientId: "synthetic-client",
          clientSecret: "synthetic-secret",
          authorizationUrl: `${issuer}/api/auth/oauth2/authorize`,
          tokenUrl: `${issuer}/api/auth/oauth2/token`,
          userInfoUrl: `${issuer}/api/auth/oauth2/userinfo`,
          scopes: ["openid", "profile", "email"],
          authorizationUrlParams: { idp, prompt: "login" },
        })),
      }),
    ],
  });
  assert.equal(typeof auth.api.signInSocial, "function");
  assert.equal("signInWithOAuth2" in auth.api, false);

  for (const { providerId, idp } of pairs) {
    const response = await auth.api.signInSocial({
      body: { provider: providerId, callbackURL: "/", errorCallbackURL: "/?error=1" },
      headers: new Headers({ origin }),
      asResponse: true,
    });
    assert.equal(response.status, 200);
    const result = await response.json();
    const authorization = new URL(result.url);
    assert.equal(authorization.origin, issuer);
    assert.equal(authorization.pathname, "/api/auth/oauth2/authorize");
    assert.equal(authorization.searchParams.get("idp"), idp);
    assert.equal(authorization.searchParams.get("prompt"), "login");
    assert.equal(
      authorization.searchParams.get("redirect_uri"),
      `${origin}/api/auth/callback/${providerId}`,
    );
    assert.equal(authorization.searchParams.get("client_id"), "synthetic-client");
    assert.ok(authorization.searchParams.get("state"));
    assert.ok(authorization.searchParams.get("code_challenge"));
  }
  assert.deepEqual(fetchCalls, []);

  const missing = await auth.api.signInSocial({
    body: { provider: "unregistered-provider", callbackURL: "/" },
    headers: new Headers({ origin }),
    asResponse: true,
  });
  assert.equal(missing.status, 404);
  assert.deepEqual(await missing.json(), { message: "Provider not found", code: "PROVIDER_NOT_FOUND" });
});
