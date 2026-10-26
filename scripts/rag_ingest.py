"""Embed corpus paragraphs into rag.chunks. Does not retrieve.

The command reads NVIDIA_NIM_API_KEY from the environment. It does not print
that key or PGVECTOR_DSN.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from collections.abc import Callable
from html.parser import HTMLParser
from pathlib import Path

MODEL = "nvidia/llama-nemotron-embed-1b-v2"
_BYTE_LIMIT = 8192 * 4
_COLUMNS = (
    "chunk_id",
    "parent_chunk_id",
    "path",
    "level",
    "doc_id",
    "tier",
    "event_id",
    "title",
    "source_url",
    "publisher",
    "licence",
    "attribution",
    "page",
    "paragraph",
    "lines",
    "section",
    "text",
    "text_sha256",
    "embedding",
    "embed_model",
)

Embedder = Callable[[list[str], str], list[list[float]]]
Writer = Callable[[list[dict]], None]


def split_paragraph(text: str) -> list[tuple[str, str]]:
    """Split one paragraph into slices that fit the embedding byte limit.

    `lines` is a 1-based range inside the original paragraph (`3-5`). A line
    that is itself over the limit is cut on UTF-8 boundaries and tagged `i-i`.
    """
    parts: list[tuple[str, str]] = []
    buffer: list[str] = []
    start = 1

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        piece = "\n".join(buffer)
        end = start + len(buffer) - 1
        parts.append((piece, f"{start}-{end}"))
        buffer = []

    for index, line in enumerate(text.split("\n"), start=1):
        if len(line.encode("utf-8")) > _BYTE_LIMIT:
            flush()
            start = index + 1
            for chunk in _utf8_chunks(line):
                parts.append((chunk, f"{index}-{index}"))
            continue
        candidate = line if not buffer else "\n".join([*buffer, line])
        if buffer and len(candidate.encode("utf-8")) > _BYTE_LIMIT:
            flush()
            start = index
        if not buffer:
            start = index
        buffer.append(line)
    flush()
    return parts


def sections_from_html(html: str) -> list[tuple[str, list[str]]]:
    """h1 and h2 start a section. Each p is a paragraph. script and style are ignored."""
    parser = _SectionParser()
    parser.feed(html)
    parser.close()
    return parser.sections


def rows_for_document(
    doc: dict,
    *,
    pages: list[str] | None,
    sections: list[tuple[str, list[str]]] | None,
    embedder: Embedder,
) -> list[dict]:
    """Document, then each page or section, then that parent's paragraphs."""
    doc_id = str(doc["doc_id"])
    rows: list[dict] = [
        _row(
            doc,
            path=doc_id,
            level="doc",
            parent=None,
            text=str(doc["title"]),
            page=None,
            paragraph=None,
            lines=None,
            section=None,
        )
    ]
    if pages is not None:
        for number, page_text in enumerate(pages, start=1):
            page_path = f"{doc_id}/p{number}"
            rows.append(
                _row(
                    doc,
                    path=page_path,
                    level="page",
                    parent=doc_id,
                    text="",
                    page=number,
                    paragraph=None,
                    lines=None,
                    section=None,
                )
            )
            paragraph = 0
            for block in _page_blocks(page_text):
                for piece, lines in split_paragraph(block):
                    paragraph += 1
                    rows.append(
                        _row(
                            doc,
                            path=f"{page_path}/para{paragraph}",
                            level="paragraph",
                            parent=page_path,
                            text=piece,
                            page=number,
                            paragraph=paragraph,
                            lines=lines,
                            section=None,
                        )
                    )
    if sections is not None:
        for number, (heading, paragraphs) in enumerate(sections, start=1):
            section_path = f"{doc_id}/s{number}"
            rows.append(
                _row(
                    doc,
                    path=section_path,
                    level="section",
                    parent=doc_id,
                    text=heading,
                    page=number,
                    paragraph=None,
                    lines=None,
                    section=heading,
                )
            )
            paragraph = 0
            for block in paragraphs:
                for piece, lines in split_paragraph(block):
                    paragraph += 1
                    rows.append(
                        _row(
                            doc,
                            path=f"{section_path}/para{paragraph}",
                            level="paragraph",
                            parent=section_path,
                            text=piece,
                            page=number,
                            paragraph=paragraph,
                            lines=lines,
                            section=heading,
                        )
                    )
    _attach_embeddings(rows, embedder)
    return rows


def ingest(root: Path, *, embedder: Embedder, writer: Writer) -> int:
    """Read the manifest, embed passages, and hand rows to `writer`."""
    import rag_corpus

    text = (root / "corpus" / "manifest.yaml").read_text(encoding="utf-8")
    for entry in rag_corpus.parse_manifest(text):
        pages, sections = _load_entry(root, entry)
        writer(rows_for_document(entry, pages=pages, sections=sections, embedder=embedder))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        print("rag ingest: unexpected arguments", file=sys.stderr)
        return 2
    dsn = os.environ.get("PGVECTOR_DSN", "")
    if not dsn:
        print("rag ingest: PGVECTOR_DSN is not set", file=sys.stderr)
        return 1
    key = os.environ.get("NVIDIA_NIM_API_KEY", "")
    if not key:
        print("rag ingest: NVIDIA_NIM_API_KEY is not set", file=sys.stderr)
        return 1
    url = os.environ.get("NIM_EMBEDDINGS_URL", "")
    root = Path(__file__).resolve().parents[1]
    agents = root / "agents"
    if str(agents) not in sys.path:
        sys.path.insert(0, str(agents))
    scripts = root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from floodsense_agents.nim_embed import DEFAULT_URL, embed_texts

    def embedder(texts: list[str], input_type: str) -> list[list[float]]:
        return embed_texts(texts, input_type, root=root, api_key=key, url=url or DEFAULT_URL)

    def writer(rows: list[dict]) -> None:
        _write_rows(dsn, rows)

    try:
        return ingest(root, embedder=embedder, writer=writer)
    except Exception as exc:
        message = str(exc)
        if (dsn and dsn in message) or (key and key in message):
            message = "rag ingest: failed"
        print(message, file=sys.stderr)
        return 1


def _utf8_chunks(line: str) -> list[str]:
    data = line.encode("utf-8")
    chunks: list[str] = []
    start = 0
    while start < len(data):
        end = min(start + _BYTE_LIMIT, len(data))
        if end < len(data):
            while end > start and (data[end] & 0xC0) == 0x80:
                end -= 1
        chunks.append(data[start:end].decode("utf-8"))
        start = end
    return chunks


def _page_blocks(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    return [block.strip() for block in re.split(r"\n\s*\n", stripped) if block.strip()]


def _row(
    doc: dict,
    *,
    path: str,
    level: str,
    parent: str | None,
    text: str,
    page: int | None,
    paragraph: int | None,
    lines: str | None,
    section: str | None,
) -> dict:
    if len(path) > 128:
        raise ValueError("chunk_id is longer than 128 characters")
    return {
        "chunk_id": path,
        "parent_chunk_id": parent,
        "path": path,
        "level": level,
        "doc_id": doc["doc_id"],
        "tier": doc["tier"],
        "event_id": doc.get("event_id"),
        "title": doc["title"],
        "source_url": doc["url"],
        "publisher": doc["publisher"],
        "licence": doc["licence"],
        "attribution": doc["attribution"],
        "page": page,
        "paragraph": paragraph,
        "lines": lines,
        "section": section,
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "embedding": None,
        "embed_model": None,
    }


def _attach_embeddings(rows: list[dict], embedder: Embedder) -> None:
    indexes = [index for index, row in enumerate(rows) if row["level"] == "paragraph"]
    if not indexes:
        return
    vectors = embedder([rows[index]["text"] for index in indexes], "passage")
    if len(vectors) != len(indexes):
        raise ValueError("embedder returned the wrong number of vectors")
    for index, vector in zip(indexes, vectors, strict=True):
        rows[index]["embedding"] = vector
        rows[index]["embed_model"] = MODEL


def _load_entry(root: Path, entry: dict) -> tuple[list[str] | None, list[tuple[str, list[str]]] | None]:
    path = root / "corpus" / str(entry["path"])
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pages_from_pdf(path.read_bytes()), None
    if suffix in {".html", ".htm"}:
        return None, sections_from_html(path.read_text(encoding="utf-8"))
    raise ValueError(f"unsupported corpus file: {path.name}")


def _pages_from_pdf(data: bytes) -> list[str]:
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return [page.extract_text() or "" for page in reader.pages]


def _write_rows(dsn: str, rows: list[dict]) -> None:
    import psycopg

    names = ", ".join(_COLUMNS)
    placeholders = ", ".join("%s::vector" if name == "embedding" else "%s" for name in _COLUMNS)
    insert = f"INSERT INTO rag.chunks ({names}) VALUES ({placeholders})"
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                for doc_id in dict.fromkeys(row["doc_id"] for row in rows):
                    cur.execute("DELETE FROM rag.chunks WHERE doc_id = %s", (doc_id,))
                for row in rows:
                    values = []
                    for name in _COLUMNS:
                        value = row[name]
                        if name == "embedding" and value is not None:
                            value = "[" + ",".join(str(item) for item in value) + "]"
                        values.append(value)
                    cur.execute(insert, values)
            conn.commit()
    except Exception:
        raise RuntimeError("rag ingest: database write failed") from None


class _SectionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[tuple[str, list[str]]] = []
        self._heading: str | None = None
        self._paragraphs: list[str] = []
        self._skip = 0
        self._in_heading = 0
        self._in_paragraph = 0
        self._heading_parts: list[str] = []
        self._paragraph_parts: list[str] = []

    def close(self) -> None:
        super().close()
        self._flush()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip += 1
            return
        if self._skip:
            return
        if tag in {"h1", "h2"}:
            self._flush()
            self._heading = ""
            self._in_heading += 1
            self._heading_parts = []
        elif tag == "p":
            self._in_paragraph += 1
            if self._in_paragraph == 1:
                self._paragraph_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
            return
        if self._skip:
            return
        if tag in {"h1", "h2"} and self._in_heading:
            self._in_heading -= 1
            if self._in_heading == 0:
                self._heading = "".join(self._heading_parts).strip()
                self._heading_parts = []
        elif tag == "p" and self._in_paragraph:
            self._in_paragraph -= 1
            if self._in_paragraph == 0:
                text = "".join(self._paragraph_parts).strip()
                self._paragraph_parts = []
                if text:
                    if self._heading is None:
                        self._heading = ""
                    self._paragraphs.append(text)

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._in_heading:
            self._heading_parts.append(data)
        elif self._in_paragraph:
            self._paragraph_parts.append(data)

    def _flush(self) -> None:
        if self._heading is None and not self._paragraphs:
            return
        self.sections.append((self._heading or "", list(self._paragraphs)))
        self._heading = None
        self._paragraphs = []


if __name__ == "__main__":
    raise SystemExit(main())
