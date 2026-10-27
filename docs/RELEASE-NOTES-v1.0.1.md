# FloodSense EU 1.0.1: release notes

Open Agent Hackathon 2026, Track 02. Released 27 Oct 2026. This is the version to submit. It replaces 1.0.0 and adds no features. The full change list is [CHANGELOG.md](../CHANGELOG.md). The product is described in [RELEASE-NOTES-v1.0.0.md](RELEASE-NOTES-v1.0.0.md).

## What changed

- **Removed the test-only alternative LLM provider switch**, end to end: agents, API, UI, evals, console and `.env.example` files. Chat runs only through Meterless Nightshift with NVIDIA Nemotron models.
- **No hallucination percentages** on the product surface (the Checked line, the Review page, the operator console and the committed eval reports). Answers are described as cited and judged.
- **Lane wording.** Both lanes (`meterless/fast`, `meterless/deep`) use Nemotron models chosen by Nightshift. Nemotron 3.5 Lightning 30B A3B answered every call recorded on 27 Oct 2026.
- **Cache keys** no longer include the provider, so existing cache entries miss once. Nothing stale is served.

## Run it

Follow the Quick start in [README.md](../README.md): `py tasks.py init-env`, `up-all`, `zetaris-sync`, `demo-seed`, then open `http://127.0.0.1:15173/`. You need your own local Zetaris and Nightshift.
