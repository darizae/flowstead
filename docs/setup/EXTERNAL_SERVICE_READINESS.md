# External service readiness — Flowstead application

**Status:** technical nonsecret prerequisites ONLY. This document is not permission to create cloud resources, modify domain DNS, enable paid plans, deploy publicly, or access production data. Work is locally testable; do not block local tasks while optional external accounts are prepared.

## Verified resources (2026-11-17)

| Resource | Verified / required target |
| --- | --- |
| Code repository | `darizae/flowstead`, PRIVATE, main; reuse |
| Supabase development project | `flowstead-dev`, ref `jryvzjwsrxctjeawnkqo`, `eu-west-1`; owner-confirmed local MCP OAuth, agent must verify real read-only query |
| Vercel team | `daniel-arizas-projects` (`team_7CJgbGIXE7hWVUqNIoWncUg8`) |
| Existing apex domain | `darizae.dev`, verified, Vercel DNS; **already serves an unrelated `personal-website` project** |
| Existing root site protection | MUST NOT repoint/transfer the apex, replace existing DNS records, alter `personal-website` or remove its custom domain |
| Proposed future frontend | `flowstead.darizae.dev` only once a separate app deployment and explicit publication are approved |
| Proposed future API | `api.flowstead.darizae.dev` only if actual chosen backend host supports custom HTTPS and owner approves it |
| AWS account and S3 | **NOT VERIFIED / NOT CREATED BY THIS PROJECT**; no assumption of Free eligibility, bucket, permission or API keys |
| Candidate Python hosting | Render Free is candidate **only**, not selected; do not deploy or link GitHub without separate approval |

## Local agent read-only preflight

1. Verify the active local Vercel CLI login. If missing, request owner browser login using `vercel login`. Select **`vercel switch daniel-arizas-projects`**. Confirm the existing domain and project; no DNS writes.
2. Check whether AWS CLI v2.32+ exists using `aws --version`. If the owner already has a scoped non-root local profile, use `aws sts get-caller-identity --profile flowstead-dev` only to verify identity. **Do not execute `aws login` as account root in an autonomous agent session.** A named browser-based `aws login --profile flowstead-dev` may be used after owner-created restricted IAM permissions; OMP must stop for owner MFA if needed.
3. Do not create AWS user, IAM role, bucket, object or budget autonomously unless a separate owner-approved cloud task names the exact resource and states the permission policy and cost/usage guard. Any policy draft should be restricted to one named bucket and key prefix, not administrator or account-wide S3.
4. Check environment/secret **names**, never print real token/password values. Sensitive credentials belong to ignored private local runtime, CLI OAuth stores, or hosting secrets, not Git.
5. Provide a concise PASS/FAIL matrix for Vercel domain visibility, root protection, AWS existence/plan, MFA, scoped local AWS CLI identity and billing safeguards. A failed external preflight must not block unrelated local development.

## Security boundaries for future S3 integration

- Use a globally unique, owner-approved bucket name, PRIVATE Block Public Access (all four controls), bucket-owner enforced ownership, encryption; prefer `eu-west-1` to match dev Supabase unless separately reviewed.
- Limit IAM actions to required bucket/objects and approved prefixes; no public access, root access keys, `s3:*` account-wide grants, source data from DHI, automatic billing upgrades or uncontrolled uploads.
- Apply hard row/time-window/object-size/request caps; routine local tests remain cloud-free. Validate a tiny independent synthetic object after authorization, and record its cleanup.
- AWS temporary CLI sessions eventually expire; never claim one OAuth login enables indefinite remote cloud writes. A future deployed service must use approved workload credentials rather than a Mac user's key.

## Provider boundary

The application repository owns deployment configuration, backend/frontend URLs, external I/O, Postgres/Supabase Auth, API per-Plant authorization and S3 adapter. The independent generator `darizae/flowstead-sim` owns **local deterministic synthetic data**; it has no required AWS, DNS, Supabase or Vercel integration.

Official references: https://vercel.com/docs/domains/managing-dns-records ; https://vercel.com/docs/cli ; https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html ; https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html ; https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html
