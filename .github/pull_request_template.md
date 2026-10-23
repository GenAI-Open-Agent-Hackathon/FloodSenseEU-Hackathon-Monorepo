## Summary

<!-- What changed, in a few sentences. -->

## Linked issue or ADR

<!-- Issue number, ADR path, or "none". -->

## Type of change

<!-- Apply the matching label so generated release notes can group this pull request.
enhancement → Features. bug → Fixes. documentation → Docs & ADRs. ci → CI & Tooling.
Anything else lands under Other. There are no agents, data, api, or ui labels yet. -->

## How it was tested

<!-- Commands you ran, and what you saw. -->

## Changelog entry

<!-- Required. Paste the line you added under ## [Unreleased] in CHANGELOG.md.
If this pull request should not appear in the notes, write `skip-changelog` and apply that label. -->

## Checklist

- [ ] `python tasks.py test` passes
- [ ] `python tasks.py lint` passes
- [ ] No secrets: no filled `.env`, no `nvapi-` key, no tokens in fixtures, logs, or screenshots
- [ ] Contracts are unchanged, or the change was announced at the 14:00 check-in
