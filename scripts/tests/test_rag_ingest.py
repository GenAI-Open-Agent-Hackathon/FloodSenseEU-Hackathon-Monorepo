"""Ingest the corpus into rag.chunks. No network and no database."""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rag_ingest  # noqa: E402

_DOC = {
    "doc_id": "easyxlab-s19",
    "title": "S19",
    "publisher": "EasyxLab",
    "url": "https://easybyte.es/lab/studies/s19/paper/",
    "licence": "CC-BY-4.0",
    "attribution": "EasyxLab (2026), Study S19, CC BY 4.0",
    "tier": 2,
    "event_id": "EMSR773",
}


def _embedder(texts: list[str], input_type: str) -> list[list[float]]:
    if input_type != "passage":
        raise AssertionError(input_type)
    return [[0.0] * 2047 + [1.0] for _ in texts]


class IngestTest(unittest.TestCase):
    def test_long_paragraph_splits_on_lines_and_parents_have_no_embedding(self) -> None:
        line = "word " * 10
        # 8192 * 4 bytes is the limit. Two blocks of lines cross it.
        text = "\n".join([line] * 4000)
        parts = rag_ingest.split_paragraph(text)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(piece.encode("utf-8")) <= 8192 * 4 for piece, _lines in parts))
        start, end = (int(part) for part in parts[0][1].split("-"))
        self.assertEqual(start, 1)
        self.assertEqual(end - start + 1, parts[0][0].count("\n") + 1)
        rows = rag_ingest.rows_for_document(
            {
                "doc_id": "easyxlab-s19",
                "title": "S19",
                "publisher": "EasyxLab",
                "url": "https://easybyte.es/lab/studies/s19/paper/",
                "licence": "CC-BY-4.0",
                "attribution": "EasyxLab (2026), Study S19, CC BY 4.0",
                "tier": 2,
                "event_id": "EMSR773",
            },
            pages=None,
            sections=[("Unmapped places", ["Outside every zone."])],
            embedder=_embedder,
        )
        kinds = [row["level"] for row in rows]
        self.assertEqual(kinds[0], "doc")
        self.assertIn("section", kinds)
        self.assertIn("paragraph", kinds)
        para = next(row for row in rows if row["level"] == "paragraph")
        self.assertGreaterEqual(para["page"], 1)
        self.assertGreaterEqual(para["paragraph"], 1)
        self.assertTrue(para["lines"])
        self.assertIsNone(next(row["embedding"] for row in rows if row["level"] == "doc"))
        self.assertEqual(para["embed_model"], "nvidia/nemotron-3.5-embed-1b")
        self.assertEqual(len(para["embedding"]), 2048)
        self.assertNotIn("retrieve_docs", Path(rag_ingest.__file__).read_text(encoding="utf-8"))

    def test_overlong_line_is_cut_on_utf8_boundaries(self) -> None:
        line = "á" * (8192 * 3)
        parts = rag_ingest.split_paragraph(line)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(tag == "1-1" for _piece, tag in parts))
        self.assertTrue(all(len(piece.encode("utf-8")) <= 8192 * 4 for piece, _tag in parts))
        self.assertEqual("".join(piece for piece, _tag in parts), line)

    def test_pdf_pages_keep_a_page_number_and_an_empty_page_has_no_paragraph(self) -> None:
        rows = rag_ingest.rows_for_document(
            {**_DOC, "doc_id": "hess-29-6715-2025"},
            pages=["", "Alpha.\n\nBeta."],
            sections=None,
            embedder=_embedder,
        )
        self.assertEqual(
            [row["level"] for row in rows],
            ["doc", "page", "page", "paragraph", "paragraph"],
        )
        paras = [row for row in rows if row["level"] == "paragraph"]
        self.assertEqual(paras[0]["path"], "hess-29-6715-2025/p2/para1")
        self.assertEqual(paras[0]["chunk_id"], paras[0]["path"])
        self.assertLessEqual(len(paras[0]["chunk_id"]), 128)
        self.assertEqual(paras[0]["page"], 2)
        self.assertEqual(paras[0]["paragraph"], 1)
        self.assertIsNone(paras[0]["section"])
        self.assertEqual(
            paras[0]["text_sha256"],
            hashlib.sha256(paras[0]["text"].encode()).hexdigest(),
        )
        self.assertIsNone(next(row["embedding"] for row in rows if row["level"] == "page"))

    def test_html_sections_skip_script_and_style(self) -> None:
        html = (
            "<h1>Title</h1><p>Alpha</p><script>SECRET</script>"
            "<style>.x{}</style><h2>Next</h2><h3>Detail</h3><p>Beta</p>"
        )
        sections = rag_ingest.sections_from_html(html)
        self.assertEqual(sections, [("Title", ["Alpha"]), ("Next", ["Beta"])])

    def test_missing_dsn_returns_before_nim(self) -> None:
        def forbid(*_args, **_kwargs):
            raise AssertionError("NIM was called")

        agents = Path(__file__).resolve().parents[2] / "agents"
        sys.path.insert(0, str(agents))
        env = {key: value for key, value in os.environ.items() if key != "PGVECTOR_DSN"}
        with patch.dict(os.environ, env, clear=True), patch(
            "floodsense_agents.nim_embed.embed_texts", forbid
        ):
            code = rag_ingest.main([])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
