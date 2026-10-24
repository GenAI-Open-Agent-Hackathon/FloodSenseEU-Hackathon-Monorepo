# Releases

How a change on `main` becomes a tag and a GitHub Release. The version numbers are the ones in [GAMEPLAN.md](GAMEPLAN.md). This file is the procedure.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

| Tag | When |
| --- | --- |
| `v0.MINOR.0` | One daily increment, at the 20:00 demo. |
| `v0.MINOR.PATCH` | A fix on an increment that already has a tag. |
| `v1.0.0-rc.N` | A release candidate. `v1.0.0-rc.1` is the Monday demo freeze. |

Tags are annotated. They are not moved, deleted, or recreated. A mistake gets the next tag. Mihir creates the tag once `main` is green.

Notes live in [CHANGELOG.md](../CHANGELOG.md), in [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) form.

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

`v0.0.0` is already tagged on `eacf34c`. Do not move it.
