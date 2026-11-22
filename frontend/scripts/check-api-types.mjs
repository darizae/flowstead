// Audit #29: fail when either checked-in contract artifact is stale.
//   1. `frontend/openapi.json` must match the live FastAPI OpenAPI document.
//   2. `src/lib/api/generated/*` must match a fresh run of the generator over
//      that committed OpenAPI document.
// Runs only read-only comparisons into a throwaway directory and never mutates
// the working tree. Invoked via `pnpm run api:types:check`.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tmp = mkdtempSync(join(tmpdir(), "flowstead-api-types-check-"));

const committedOpenapi = join(root, "openapi.json");
const committedGenDir = join(root, "src", "lib", "api", "generated");
const REPO_BACKEND = join(root, "..", "backend");
const OPENAPI_SCRIPT = join(root, "..", "scripts", "generate_openapi.py");
const OPENAPI_TS_BIN = join(root, "node_modules", ".bin", "openapi-ts");

// `openapi-ts` embeds the input path in `ClientOptions.baseUrl`, so the TS
// regeneration must read the committed `openapi.json` by its stable relative
// name; the OpenAPI freshness check below covers the live document instead.
const genFreshDir = join(tmp, "gen");

try {
  // 1. Live FastAPI document vs committed OpenAPI snapshot.
  const openapiFresh = join(tmp, "openapi.json");
  execFileSync(
    "uv",
    ["run", "--project", REPO_BACKEND, "python", OPENAPI_SCRIPT, openapiFresh],
    { stdio: "inherit" },
  );

  // 2. Generator output over the committed OpenAPI vs checked-in generated types.
  execFileSync(
    OPENAPI_TS_BIN,
    [
      "-i",
      "openapi.json",
      "-o",
      genFreshDir,
      "--plugins",
      "@hey-api/typescript",
      "--no-log-file",
    ],
    { stdio: "inherit" },
  );

  const comparisons = [
    ["OpenAPI document", openapiFresh, committedOpenapi],
    ["generated TS types", join(genFreshDir, "types.gen.ts"), join(committedGenDir, "types.gen.ts")],
    ["generated index", join(genFreshDir, "index.ts"), join(committedGenDir, "index.ts")],
  ];

  const stale = comparisons.filter(([, fresh, committed]) => {
    const a = readFileSync(fresh);
    const b = readFileSync(committed);
    return a.length !== b.length || !a.equals(b);
  });
  if (stale.length === 0) {
    console.log("API contract is up to date.");
  } else {
    console.error(
      "API contract is stale. Run `pnpm run api:types` and commit the changes.",
    );
    for (const [label] of stale) console.error(`  - ${label}`);
    process.exitCode = 1;
  }
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
