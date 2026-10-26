"""retrieve_docs and its Investigator hook. No network."""

from __future__ import annotations

import hashlib
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.retrieve_docs import retrieve_docs  # noqa: E402
from floodsense_agents.state import Deps, NoMemory  # noqa: E402
from floodsense_agents.zetaris import FakeZetaris  # noqa: E402
from tests.test_graph import start  # noqa: E402


class RetrieveDocsTest(unittest.TestCase):
    def test_empty_search_returns_no_citations(self) -> None:
        def hydrate(ids):
            raise AssertionError(ids)

        result = retrieve_docs(
            "rain in Paiporta",
            4,
            {"event_id": "EMSR773"},
            embedder=lambda texts, input_type: [[0.0] * 2048],
            search=lambda vector, event_id, k: [],
            hydrate=hydrate,
        )
        self.assertEqual(result.citations, [])
        self.assertIsNone(result.error)

    def test_k_out_of_range_is_a_tool_error(self) -> None:
        def unused(*_args, **_kwargs):
            raise AssertionError("k is rejected before embed, search, or hydrate")

        result = retrieve_docs(
            "q", 0, {"event_id": "EMSR773"}, embedder=unused, search=unused, hydrate=unused
        )
        self.assertEqual(result.citations, [])
        self.assertIn("1 to 20", result.error)

    def test_quote_is_a_substring_and_hashes(self) -> None:
        text = "line one\nline two stays under six hundred"
        row = {
            "chunk_id": "hess-29-6715-2025/p12/para3",
            "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "title": "HESS",
            "source_url": "https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf",
            "publisher": "Copernicus Publications",
            "licence": "CC-BY-4.0",
            "attribution": "Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0",
            "page": 12,
            "paragraph": 3,
            "lines": "1-2",
            "section": None,
        }

        def embedder(texts, input_type):
            self.assertEqual(input_type, "query")
            return [[0.1] * 2048]

        result = retrieve_docs(
            "rainfall",
            1,
            {"event_id": "EMSR773"},
            embedder=embedder,
            search=lambda vector, event_id, k: [(row["chunk_id"], 0.2)],
            hydrate=lambda ids: ("qid-9", [row]),
        )
        citation = result.citations[0]
        self.assertEqual(citation["query_id"], "qid-9")
        self.assertEqual(citation["storage"], "full_text")
        self.assertIn(citation["quote"], text)
        self.assertLessEqual(len(citation["quote"]), 600)
        self.assertEqual(
            citation["content_sha256"], hashlib.sha256(citation["quote"].encode()).hexdigest()
        )
        self.assertEqual(citation["locator"]["page"], 12)
        self.assertEqual(citation["chunk_id"], row["chunk_id"])
        self.assertNotIn("distance", citation)

    def test_missing_hydrate_row_is_dropped(self) -> None:
        kept = {
            "chunk_id": "kept",
            "text": "The Ahr rose at Altenahr.",
            "text_sha256": hashlib.sha256(b"The Ahr rose at Altenahr.").hexdigest(),
            "title": "EMSR517",
            "source_url": "https://mapping.emergency.copernicus.eu/activations/EMSR517",
            "publisher": "Copernicus Emergency Management Service",
            "licence": "CEMS On-Demand Mapping terms",
            "attribution": "Copernicus Emergency Management Service (© 2021 European Union), EMSR517",
            "page": 1,
            "paragraph": 1,
            "lines": "1-1",
            "section": None,
        }
        result = retrieve_docs(
            "q",
            2,
            {"event_id": "EMSR517"},
            embedder=lambda texts, input_type: [[0.0] * 2048],
            search=lambda vector, event_id, k: [("kept", 0.1), ("gone", 0.2)],
            hydrate=lambda ids: ("qid", [kept]),
        )
        self.assertEqual([c["chunk_id"] for c in result.citations], ["kept"])

    def test_other_nodes_do_not_name_the_tool(self) -> None:
        root = Path(__file__).resolve().parents[1] / "floodsense_agents" / "nodes"
        for name in ("watchers.py", "exposure.py", "skeptic.py"):
            text = (root / name).read_text(encoding="utf-8")
            self.assertNotIn("retrieve_docs", text)

    def test_a_run_without_doc_query_does_not_retrieve(self) -> None:
        def boom(*_args, **_kwargs):
            raise AssertionError("retrieve_docs was called")

        for flag in (True, False):
            bundle = Deps(
                zetaris=FakeZetaris(),
                llm=FakeNightshift(),
                memory=NoMemory(),
                retrieve_docs=boom,
            )
            graph = build_graph(
                bundle,
                MemorySaver(),
                ff_rag_docs=flag,
                ff_skeptic=False,
                ff_judge=False,
            )
            out, _ = start(graph, rid=f"rag-{flag}")
            self.assertNotIn("retrieve_docs error", str(out.get("trace")))


if __name__ == "__main__":
    unittest.main()
