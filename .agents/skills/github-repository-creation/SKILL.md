---
name: github-repository-creation
description: Create and verify the specifically authorized private Flowstead remote during initialization only.
---

# GitHub repository creation — approved initialization only

Use only for task 001 and the exact approved `darizae/flowstead` remote. It does not authorize extra repositories, deletion, public visibility, force-push, paid operations or releases.

## Prerequisites

Confirm exact OWNER/REPO, private visibility, `main`, clean status, no conflicting origin, authenticated `gh auth status --active`, and absent remote. Never print tokens. Review `AGENTS.md`, `README.md`, `justfile`, `.gitignore`, planning contract/task files and this skill. Ensure `priv/`, credentials and environment files are ignored.

## Create and verify

From this local root, initialize `main` if needed, commit only reviewed scaffold files, then create the exact private remote with `gh repo create darizae/flowstead --private --source=. --remote=origin` and push `git push -u origin main`. Never use `--add-readme`, overwrite an existing remote, or force-push. A create-without-push is partial and must be reported.

Verify `gh repo view darizae/flowstead --json nameWithOwner,visibility,defaultBranchRef,url`, `git remote get-url origin`, `git rev-parse HEAD`, `git ls-remote --heads origin main`, and `git status --short`; compare local and remote SHAs. Do not mark done without matching private `main` evidence.
