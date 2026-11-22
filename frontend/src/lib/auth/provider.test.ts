import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createDefaultAuthProvider,
  FailClosedAuthProvider,
  TestAuthProvider,
} from "./provider";

type AuthGlobal = { __FLOWSTEAD_TEST_AUTH__?: unknown };
const authGlobal = globalThis as AuthGlobal;

afterEach(() => {
  delete authGlobal.__FLOWSTEAD_TEST_AUTH__;
  vi.unstubAllEnvs();
});

describe("#39 production auth provider fails closed", () => {
  it("returns a fail-closed provider (never the TestAuthProvider seam) when Supabase is unconfigured", async () => {
    vi.stubEnv("VITE_SUPABASE_URL", "");
    vi.stubEnv("VITE_SUPABASE_ANON_KEY", "");
    const provider = createDefaultAuthProvider();
    expect(provider).toBeInstanceOf(FailClosedAuthProvider);
    expect(provider).not.toBeInstanceOf(TestAuthProvider);
    expect(provider.getSession()).toBeNull();
    await expect(
      provider.signIn?.("op@example.com", "s3cret"),
    ).rejects.toThrow();
  });

  it("keeps the unit/browser test injection seam", () => {
    const injected = new TestAuthProvider(null, {
      email: "op@example.com",
      password: "s3cret",
      principalId: "principal-a",
    });
    authGlobal.__FLOWSTEAD_TEST_AUTH__ = injected;
    expect(createDefaultAuthProvider()).toBe(injected);
  });
});
