# Frontend package manager migration and dependency audit — November 22, 2026

## Original issue

Before this change the frontend used **npm** and committed `frontend/package-lock.json`. Consequently `pnpm audit` failed with `ERR_PNPM_AUDIT_NO_LOCKFILE` — pnpm cannot audit an npm lockfile. The prior **full** `npm audit` reported four high-severity affected packages, all reached through the same development-only vulnerable `js-yaml@4.2.0`:

```text
@hey-api/openapi-ts@0.99.0 (dev-only OpenAPI TypeScript generator)
├── @hey-api/json-schema-ref-parser@1.4.4
│   └── js-yaml@4.2.0 (vulnerable; pinned exactly by the parser)
└── @hey-api/shared@0.5.0
    └── @hey-api/json-schema-ref-parser@1.4.4 (same parser)
```

npm counted upstream affected packages in addition to `js-yaml`, not four unrelated vulnerable application dependencies. The YAML parser advisories concern potentially quadratic CPU use for adversarial merge keys and `!!omap` values: [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m), [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj), [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh). `@hey-api/openapi-ts` runs when generating TypeScript source during development, not inside the shipped React bundle, but was still patched.

## Migration and safe remediation

The frontend now uses **pnpm 11.1.3**, pinned with `packageManager` in `frontend/package.json`. The npm lockfile was imported with `pnpm import`, checked into `frontend/pnpm-lock.yaml`, and **removed**. `pnpm install --frozen-lockfile` reproduces the dependency graph. There is no root JS workspace; run commands from `frontend/` or use `pnpm --dir frontend` from the repository root.

`@hey-api/json-schema-ref-parser@1.4.4` pins vulnerable `js-yaml` exactly to `4.2.0`. Rather than downgrade `@hey-api/openapi-ts@0.99.0` or regenerate contracts with a different compiler, `frontend/pnpm-workspace.yaml` applies this explicit resolution override:

```yaml
packages:
  - .
overrides:
  js-yaml: 4.3.2
```

pnpm 11 requires the override in **`pnpm-workspace.yaml`**, not npm's `overrides` field in `package.json` or the old `pnpm.overrides` manifest field. `pnpm why js-yaml` confirms **one installed `js-yaml@4.3.2`**, shared by the OpenAPI parser and ESLint; the generated API TypeScript declarations still match the committed schema. The fix stays within the v4 public API and avoids `npm audit fix --force`. Keep the override until upstream no longer pins a vulnerable version; remove it only after auditing and verifying a newly generated lockfile.

## Reproducible commands

From `frontend/`, using Node **26.13.1** as pinned in `.node-version` and pnpm **11.1.3** as pinned in `package.json`:

```sh
pnpm install --frozen-lockfile
pnpm why js-yaml
pnpm audit --audit-level=moderate
pnpm audit --prod --audit-level=moderate
pnpm run api:types:check
pnpm run lint
pnpm run format:check
pnpm run typecheck
pnpm run test:coverage
pnpm run build
```

On November 22, **both the full pnpm audit and `pnpm audit --prod` reported zero vulnerabilities**. The frontend check/build and generated contract check were re-run after the pnpm install. The migration also updates the root `justfile`, pre-commit, browser E2E runner, Vercel build command and the checked-in GitHub Actions install/cache commands so future automation uses the committed pnpm lockfile. **Do not run or troubleshoot remote GitHub Actions until December 1, 2026**: GitHub previously blocked all jobs due to account billing/spending limits, and the owner explicitly paused CI investigation. A push during the pause uses `[skip ci]`.

Historical task records, previous local audit receipts and older acceptance snapshots still mention npm as provenance for tests performed **before** this migration. Do not reinterpret them as current setup instructions.
