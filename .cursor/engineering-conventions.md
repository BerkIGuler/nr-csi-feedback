---
status: draft
nfr: NFR-10
---

# Engineering conventions

Branch names, commits, pull requests, and the M0 toolchain seed below are decided. Code placement is by **architecture layer**, not a frozen tree — see `docs/design/layers.md`.

## Branch names

Two long-lived branches. Short-lived work never merges to `main` except as noted under hotfixes.

| Branch | Role |
| --- | --- |
| `main` | Last **released** milestone. Update only by merging `dev` (or a hotfix) and tagging (`v0.1.0`, …). |
| `dev` | **Release buffer.** Integration branch. All ordinary PRs target `dev`. |

Flow:

```text
feat/* fix/* docs/* chore/*
        │
        ▼
       dev          # integrate; M1 stays here until test-complete
        │
        │  milestone accepted (§11)
        ▼
       main + tag   # e.g. v0.1.0
```

`dev` may be ahead of `main`. It is not a second product: it is unreleased work. Do not tag `dev`. Do not open feature PRs against `main`.

### Short-lived branches

Prefix, then a kebab-case name. Feature branches **include the milestone** so M2+ work is obvious before M1 is done.

| Prefix | Role | Example |
| --- | --- | --- |
| `feat/<milestone>-<name>` | One capability | `feat/m1-cqi-threshold-table` |
| `fix/<name>` | One bug on unreleased work | `fix/cqi-index-off-by-one` |
| `docs/<name>` | Design / conventions / README | `docs/nfr-test-oracles` |
| `chore/<name>` | CI, packaging, tooling | `chore/ci-pytest` |
| `temp/<name>` | Local spike | `temp/try-polar-uci` |

`temp/*` is never merged and should not be pushed long-term. Delete it when the spike is done or reborn as `feat/` / `docs/`.

Do not use `integrate/` or `test/` prefixes. Extra tests are `feat/` or `chore/`. Stacking work is a PR into `dev`, not a branch type.

### Hotfixes (after a tag)

If `main` is already tagged and `dev` has later milestone work, a patch to the release branches off `main` as `fix/<name>`, merges to `main` (new patch tag if needed), then **back-merges into `dev`** so the buffer does not lose the fix.

## Commits

Commits **must** be frequent and thin. Each commit is **one intent** (one reason to revert). Related files follow from that intent; “all of this directory” or a drive-by docs rewrite mixed with code is too coarse.

Tests that lock the new behavior **must** land in the same commit. A red history on `dev` makes `git bisect` useless.

### Message

```text
feat(m1): map post-eq SINR through the CQI threshold table

The exploratory mapper must use the cited table, not an inline
Shannon cutoff, so FR-13 stays inspectable.
```

- Subject: ~50–72 characters, imperative (`map`, `add`, `reject`), no trailing period.
- Prefix with `feat` / `fix` / `docs` / `chore` to match branch types. Optional scope: milestone or area (`m1`, `cqi`, `docs`).
- Subject states the change; body states **why** when that is not obvious. Do not write “updated foo.py”.
- Point at an FR, NFR, or milestone when the commit implements one. Do not require issue numbers or trailer footers.

`temp/*` spikes may use rough messages. Those commits are never merged.

### History

- Do not merge known-broken commits into `dev`.
- On `feat/*`, tiny fixup commits are fine. Before the PR, squash **fixup/typo** noise; keep the atomic commits.
- Do not amend or rewrite commits that are already on `dev` or `main`. Tidy only unpushed work on the short-lived branch.
- Do not commit secrets, `__pycache__`, large Monte Carlo dumps, or notebook checkpoints unless the notebook is the artifact.
- Formatting-only churn and behavior change are two commits (`chore:` then `feat:` / `fix:`).

A hotfix onto `main` uses `fix:` and should say it is a post-tag patch so the back-merge into `dev` is obvious.

## Pull requests

Ordinary PRs target **`dev`**. Hotfixes after a tag target **`main`**, then back-merge to `dev`. Do not open PRs from `temp/*`. Do not open M2+ feature PRs until M1 is test-complete (`docs/design/requirements.md` §10–§11).

One PR is one intent (same bar as a commit, at feature scale). Title uses the commit subject style: `feat(m1): …`. Keep the PR small enough to review in one sitting.

Every PR **must** set the GitHub sidebar **Milestone** to the product milestone it implements (M0–M8 in `docs/design/requirements.md` §10) and a type **label** (`feat`, `fix`, `docs`, `chore`) matching the branch prefix.

GitHub fills the form from `.github/PULL_REQUEST_TEMPLATE.md`.

## Code placement

There is no required module map in this file. Place new work using the layers in [`docs/design/layers.md`](../docs/design/layers.md) (L0 primitives … L5 experiments). That document is how the agent decides “new module vs method vs orchestration.”

## M0 seed

This is a starting cut so packaging is not redesigned on the first feature PR. Layers still decide *what* goes where; this only names the tools and the import root.

- **Layout:** `src/<import package>/` and `tests/`, `pyproject.toml`. Language and import name: NFR-1 and NFR-2 in `docs/design/requirements.md`.
- **Tests:** pytest.
- **Lint/format:** Ruff (`ruff check` and `ruff format`). One tool; no Black/Flake8 split.
- **CI:** GitHub Actions on pull requests. The workflow **must** run pytest and Ruff. That is what “CI green” means on the PR template.
- **Local hook:** optional pre-commit that runs the same Ruff commands. Convenience only; CI is the gate. Do not skip hooks when they are installed.
- **Do not** add a second test runner, a second formatter, or a required folder tree beyond `src/` and `tests/`.

## Out of scope here

- CSI quantities, FRs, milestones — `docs/design/requirements.md`
- Architecture layers (L0–L5) — `docs/design/layers.md`
- FR writing style — `.cursor/rules/functional-requirements.mdc`
- Project purpose and voice — `.cursor/rules/project-purpose.mdc`
- Agent reminder for this file — `.cursor/rules/engineering-conventions.mdc`
- One home per rule — `.cursor/rules/single-home.mdc`
