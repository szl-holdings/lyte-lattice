import assert from "node:assert/strict";
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
