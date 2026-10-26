"""Place the layer (c) corpus described by corpus/manifest.yaml.

`placement: git` files are already under corpus/pdf/. This command checks
their sha256 and does not download them. `placement: fetch` files are
downloaded into corpus/fetched/ and checked. Nothing is embedded, and
compose is not started.

Stdlib only. The NVIDIA key is not read.
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("corpus") / "manifest.yaml"
USER_AGENT = "floodsense-rag-corpus/1.0"
FETCH_MAX_BYTES = 1024 * 1024 * 1024
FIELDS = (
    "doc_id",
    "title",
    "publisher",
    "url",
    "licence",
    "attribution",
    "sha256",
    "tier",
    "event_id",
    "path",
    "placement",
)
_DOC_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_ITEM = re.compile(r"^- ([a-z0-9_]+): (.*)$")
_CONT = re.compile(r"^  ([a-z0-9_]+): (.*)$")
_FORBIDDEN_LICENCE = re.compile(
    r"BY-NC|BY-ND|NonCommercial|NoDerivatives",
    re.IGNORECASE,
)


class CorpusError(Exception):
    """A manifest or file problem. The message names no secret."""


def _unescape(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        char = value[i]
        if char != "\\":
            out.append(char)
            i += 1
            continue
        if i + 1 >= len(value):
            raise CorpusError("trailing backslash in a quoted value")
        nxt = value[i + 1]
        out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt))
        i += 2
    return "".join(out)


def _scalar(raw: str) -> object:
    if raw == "null":
        return None
    if raw.startswith('"'):
        if len(raw) < 2 or not raw.endswith('"'):
            raise CorpusError(f"unterminated quote: {raw[:40]}")
        return _unescape(raw[1:-1])
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    if raw == "":
        raise CorpusError("empty value")
    return raw


def parse_manifest(text: str) -> list[dict[str, object]]:
    """Parse the restricted manifest YAML this repo writes."""
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        new_item = line.startswith("- ")
        match = _ITEM.match(line) if new_item else _CONT.match(line)
        bad_item = match is not None and new_item and match.group(1) != "doc_id"
        if match is None or bad_item:
            if new_item:
                raise CorpusError(f"line {number}: expected '- doc_id: ...'")
            raise CorpusError(f"line {number}: expected 'key: value'")
        key, raw = match.group(1), match.group(2)
        if key not in FIELDS:
            raise CorpusError(f"line {number}: unknown field {key}")
        try:
            value = _scalar(raw)
        except CorpusError as exc:
            raise CorpusError(f"line {number}: {exc}") from exc
        if line.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {key: value}
        else:
            if current is None:
                raise CorpusError(f"line {number}: value before the first document")
            if key in current:
                raise CorpusError(f"line {number}: duplicate field {key}")
            current[key] = value
    if current is not None:
        entries.append(current)
    if not entries:
        raise CorpusError("manifest is empty")
    return [_check(entry, index) for index, entry in enumerate(entries, 1)]


def _check(entry: dict[str, object], index: int) -> dict[str, object]:
    missing = [key for key in FIELDS if key not in entry]
    if missing:
        raise CorpusError(f"document {index}: missing {', '.join(missing)}")
    doc_id = entry["doc_id"]
    if not isinstance(doc_id, str) or not _DOC_ID.fullmatch(doc_id):
        raise CorpusError(f"document {index}: doc_id must be lowercase words separated by hyphens")
    for key in ("title", "publisher", "licence", "attribution"):
        value = entry[key]
        if not isinstance(value, str) or not value.strip():
            raise CorpusError(f"{doc_id}: {key} must be a non-empty string")
    if _FORBIDDEN_LICENCE.search(str(entry["licence"])):
        raise CorpusError(f"{doc_id}: licence {entry['licence']} forbids storing a copy")
    url = entry["url"]
    if not isinstance(url, str) or not url.startswith("https://") or "@" in url:
        raise CorpusError(f"{doc_id}: url must be an https URL with no userinfo")
    sha = entry["sha256"]
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise CorpusError(f"{doc_id}: sha256 must be 64 lowercase hex characters")
    tier = entry["tier"]
    if tier not in (1, 2, 3):
        raise CorpusError(f"{doc_id}: tier must be 1, 2, or 3")
    event = entry["event_id"]
    if tier in (1, 2):
        if event not in ("EMSR773", "EMSR517"):
            raise CorpusError(f"{doc_id}: event_id must be EMSR773 or EMSR517")
    elif event not in (None, "EMSR773", "EMSR517"):
        raise CorpusError(f"{doc_id}: tier 3 event_id must be null, EMSR773, or EMSR517")
    placement = entry["placement"]
    if placement not in ("git", "fetch"):
        raise CorpusError(f"{doc_id}: placement must be git or fetch")
    path = entry["path"]
    prefix = "pdf" if placement == "git" else "fetched"
    if not isinstance(path, str):
        raise CorpusError(f"{doc_id}: path must be a string")
    parts = Path(path).parts
    if (
        "\\" in path
        or path.startswith("/")
        or not parts
        or parts[0] != prefix
        or any(part in ("", ".", "..") for part in parts)
    ):
        raise CorpusError(f"{doc_id}: path must stay under corpus/{prefix}/")
    return entry


def _destination(root: Path, rel: str) -> Path:
    corpus = (root / "corpus").resolve()
    dest = (corpus / rel).resolve()
    prefix = (corpus / Path(rel).parts[0]).resolve()
    if dest != prefix and prefix not in dest.parents:
        raise CorpusError(f"{rel}: path escapes corpus/")
    return dest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _http_get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            chunks: list[bytes] = []
            total = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > FETCH_MAX_BYTES:
                    raise CorpusError(f"{url}: file is larger than {FETCH_MAX_BYTES} bytes")
                chunks.append(block)
    except urllib.error.HTTPError as exc:
        raise CorpusError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise CorpusError(f"download failed for {url}: {exc.reason}") from exc
    return b"".join(chunks)


def _unique(entries: list[dict[str, object]]) -> None:
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for entry in entries:
        doc_id = str(entry["doc_id"])
        path = str(entry["path"])
        if doc_id in seen_ids:
            raise CorpusError(f"duplicate doc_id {doc_id}")
        if path in seen_paths:
            raise CorpusError(f"duplicate path {path}")
        seen_ids.add(doc_id)
        seen_paths.add(path)


def fetch_rag_corpus(root: Path, *, opener=None) -> int:
    """Check git files and download fetch files. Returns 0 on success."""
    download = _http_get if opener is None else opener
    manifest = root / MANIFEST
    if not manifest.is_file():
        print(f"missing {MANIFEST.as_posix()}", file=sys.stderr)
        return 1
    try:
        entries = parse_manifest(manifest.read_text(encoding="utf-8"))
        _unique(entries)
    except CorpusError as exc:
        print(f"rag corpus: {exc}", file=sys.stderr)
        return 1
    errors: list[str] = []
    fetched = 0
    for entry in entries:
        doc_id = str(entry["doc_id"])
        rel = str(entry["path"])
        try:
            dest = _destination(root, rel)
        except CorpusError as exc:
            errors.append(str(exc))
            continue
        expected = str(entry["sha256"])
        if entry["placement"] == "git":
            if not dest.is_file():
                errors.append(f"{doc_id}: missing corpus/{rel}")
                continue
            if _sha256(dest) != expected:
                errors.append(f"{doc_id}: sha256 does not match corpus/{rel}")
            continue
        if dest.is_file() and _sha256(dest) == expected:
            fetched += 1
            continue
        try:
            body = download(str(entry["url"]))
        except CorpusError as exc:
            errors.append(str(exc))
            continue
        except Exception as exc:  # opener failure stays a corpus error, not a traceback
            errors.append(f"{doc_id}: download failed ({exc.__class__.__name__})")
            continue
        if not isinstance(body, bytes):
            errors.append(f"{doc_id}: download did not return bytes")
            continue
        if len(body) > FETCH_MAX_BYTES:
            errors.append(f"{doc_id}: file is larger than {FETCH_MAX_BYTES} bytes")
            continue
        if hashlib.sha256(body).hexdigest() != expected:
            partial = dest.with_name(dest.name + ".partial")
            if partial.exists():
                partial.unlink()
            errors.append(f"{doc_id}: sha256 does not match {entry['url']}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".partial")
        partial.write_bytes(body)
        partial.replace(dest)
        fetched += 1
    if errors:
        for message in errors:
            print(f"rag corpus: {message}", file=sys.stderr)
        return 1
    print(f"rag corpus: {len(entries)} checked, {fetched} fetched")
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv:
        print("fetch-rag-corpus takes no arguments", file=sys.stderr)
        return 2
    return fetch_rag_corpus(ROOT)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
