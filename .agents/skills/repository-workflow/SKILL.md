---
name: repository-workflow
description: Use for commits, PRs, test and release changes in ok-infinity-nikki.
---

# Repository workflow

1. Read `AGENTS.md` and related skills, and inspect the current branch, working changes, upstream `origin/main` and complete diff before committing.
2. Branch from fresh `origin/main` and submit changes through a pull request. Do not write directly to `main`.
3. Split only work with independently changing/releasable responsibilities. Keep PR title and body truthful about behavior and dependencies.
4. Run `uv sync --locked`, focused tests, `git diff --check`, and the PR workflow checks; report verification gaps, especially non-Windows environments.
5. Preserve user changes, asset content and gitlink pointers. Never commit credentials, local config or generated caches.
6. In PR review, inspect current HEAD, all review bodies, inline threads, outside-diff findings and CI. Old approvals do not cover a new HEAD. Never manually resolve CodeRabbit threads. Fix verified findings, test, push and let the reviewer recheck before squash merging.
