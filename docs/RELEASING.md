# Releases

How a change on `main` becomes a tag and a GitHub Release. The version numbers are the ones in [GAMEPLAN.md](GAMEPLAN.md). This file is the procedure.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

| Tag | When |
| --- | --- |
| `v0.MINOR.0` | One product increment. Tagged: `v0.0.0`, `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.9.0`, `v0.12.0`, `v0.13.0`. There is no `v0.4.0`–`v0.8.0` tag. `v0.10.0` shipped inside `v0.2.0`. Planned layer (c) was formerly called `v0.11` stretch and is not a tag. The cache shipped as `v0.12.0`. This demo baseline is `v0.13.0`. RAG layer (c) will be `v0.14.0`. There is no patch ladder between `v0.9.0` and `v0.13.0`. The Monday freeze tag remains `v1.0.0-rc.1`. |
| `v1.0.0-rc.N` | A release candidate. `v1.0.0-rc.1` is the Monday demo freeze. Later candidates are `rc.2`, `rc.3`, and so on. |

Tags on the 0.x line are `v0.MINOR.0` only. There is no `v0.MINOR.PATCH` tag and no `v0.x.y` fix tag. A fix on that line lands on `main` and is included in the next minor tag. Tags are annotated. They are not moved, deleted, or recreated. A mistake is not retagged in place. The next tag is the next `v0.MINOR.0`, or the next `v1.0.0-rc.N` after the freeze. Mihir creates the tag once `main` is green.

Notes live in [CHANGELOG.md](../CHANGELOG.md), in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) form. The GitHub wiki is disabled.

## On a pull request

Add the user-visible lines under `## [Unreleased]`. The pull request template asks for that line.

If the change should stay out of the notes, do not add a line. Apply the `skip-changelog` label instead. GitHub's generated notes (`.github/release.yml`) drop that label, and they drop pull requests from `dependabot[bot]`, `github-actions[bot]`, and `renovate[bot]`.

## At the 20:00 increment

1. On green `main`, move the `## [Unreleased]` bullets into a new section `## [X.Y.Z] - YYYY-MM-DD`. Leave the `## [Unreleased]` heading in place for the next change.
2. Update the links at the bottom. `[Unreleased]` compares `vX.Y.Z...HEAD`. `[X.Y.Z]` compares the previous tag to this one. The first release links to its tag.
3. Create an annotated tag on that commit and push the tag. Do not use a lightweight tag.

```bash
git tag -a vX.Y.Z -m "vX.Y.Z: short increment name"
git push origin vX.Y.Z
```

4. Publish a GitHub Release for that existing tag. Title it `vX.Y.Z - short name`. Use the new changelog section as the notes. GitHub can draft notes from merged pull requests; `.github/release.yml` sets the groups. `enhancement` is Features, `bug` is Fixes, `documentation` is Docs & ADRs, and `ci` is CI & Tooling. Anything else is Other. `enhancement`, `bug`, and `documentation` already exist. Add `ci` and `skip-changelog` when you first apply them. There are no `agents`, `data`, `api`, or `ui` labels, so those areas have no group of their own until the labels exist. Edit the draft so the published text matches the changelog section.

Do not move the annotated tags. `v0.3.0` is live gauges and `hazard_now`. Its scope is in [GAMEPLAN.md](GAMEPLAN.md): [#24](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/24) `hazard_now` (migrations `034` and `035`), [#28](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/28) gauge views, [#29](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/29) migrations `042` and `043`, [#26](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/26) tag policy, and [#27](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/27) judge lane ids. Core sources, provenance, `ingestion/feeds/`, and migration `033` `pegel_levels` shipped in `v0.1.0`. Laptop Zetaris e2e is deferred to the morning of 26 Oct 2026. `v0.9.0` is memory: [#15](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/15) H-MEM recall, write-on-approval, the World Model bridge, and the sidecar trust ledger; [#16](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/16) short-term thread memory; [#32](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/32) the sqlite hang fix. `v0.12.0` is the semantic cache and labelled replay ([#17](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/17)). `FF_SEMANTIC_CACHE` and `FF_CACHED_REPLAY` default off. Rate limits are still a follow-up. `v0.13.0` is the demo baseline: UI shell ([#36](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/36)), audit fixes ([#37](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/37)), Zetaris sync `User-Agent` ([#30](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/30)), PR-review skill ([#35](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/35)), and the `local/` gitignore ([#39](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/39)). Planned layer (c) was formerly called `v0.11` stretch and is not a tag. The cache shipped as `v0.12.0`. RAG layer (c) will be `v0.14.0`. There is no `v0.4.0`–`v0.8.0` tag, no `v0.10.0` tag, and no patch ladder between `v0.9.0` and `v0.13.0`. The Monday freeze tag remains `v1.0.0-rc.1`. The wiki is disabled. Notes are [CHANGELOG.md](../CHANGELOG.md) and the GitHub Release.

- `v0.0.0` is the skeleton tag on `eacf34c`. Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.0.0
- `v0.1.0` is the data-slice tag on `7045fc5`. Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.1.0
- `v0.2.0` is the live demo stack on `71390b6` (agents graph, insurer desk, engines sidecar, fast lane, parallel Zetaris). Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.2.0
- `v0.3.0` is live gauges and `hazard_now`. Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.3.0
- `v0.9.0` is memory (H-MEM, World Model, thread memory, sqlite hang fix). Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.9.0
- `v0.12.0` is the semantic cache and labelled replay ([#17](https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/pull/17); flags default off; rate limits still a follow-up). Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.12.0
- `v0.13.0` is the demo baseline (UI shell, audit fixes, Valencia seed path; RAG layer (c) is `v0.14.0` and is not in this tag). Release: https://github.com/GenAI-Open-Agent-Hackathon/Hackathon-Monorepo/releases/tag/v0.13.0
