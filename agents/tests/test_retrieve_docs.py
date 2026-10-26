"""retrieve_docs and its Investigator hook. No network."""

from __future__ import annotations

import hashlib
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CHECKPOINTER", "memory")
os.environ.setdefault("ZETARIS_MODE", "fake")
os.environ.setdefault("LLM_MODE", "fake")

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from floodsense_agents import retrieve_docs as retrieve_mod  # noqa: E402
from floodsense_agents.graph import build_graph  # noqa: E402
from floodsense_agents.models import Citation, Claim, Evidence, RunRequest  # noqa: E402
from floodsense_agents.nightshift import FakeNightshift  # noqa: E402
from floodsense_agents.nodes.investigator import _attach_documents  # noqa: E402
from floodsense_agents.nodes.judge import score_claim  # noqa: E402
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

    def test_search_binds_each_reused_placeholder(self) -> None:
        """Halfvec and the exact fallback reuse $1 and $2. Each use must be bound."""

        class Cursor:
            def __init__(self) -> None:
                self.sql = ""
                self.params: object = None

            def execute(self, sql, params) -> None:
                self.sql = sql
                self.params = params

            def fetchall(self):
                return [("chunk-a", 0.2)]

            def __enter__(self):
                return self

            def __exit__(self, *_args) -> bool:
                return False

        class Conn:
            def __init__(self) -> None:
                self.cur = Cursor()

            def cursor(self) -> Cursor:
                return self.cur

            def __enter__(self) -> "Conn":
                return self

            def __exit__(self, *_args) -> bool:
                return False

        rendered = "[0.1,0.2]"
        cases = (
            (retrieve_mod._HALFVEC_SQL, "EMSR773", "EMSR773"),
            (retrieve_mod._EXACT_SQL, None, None),
        )
        original = retrieve_mod._connect
        try:
            for statement, event_id, expect_event in cases:
                self.assertEqual(statement.count("$1"), 2)
                self.assertEqual(statement.count("$2"), 2)
                self.assertEqual(statement.count("$3"), 1)
                conn = Conn()
                retrieve_mod._connect = lambda _dsn, conn=conn: conn
                rows = retrieve_mod._search(
                    "postgresql://127.0.0.1/rag", statement, [0.1, 0.2], event_id, 4
                )
                self.assertEqual(rows, [("chunk-a", 0.2)])
                self.assertEqual(_bound_values(conn.cur.sql, conn.cur.params), [
                    rendered,
                    expect_event,
                    expect_event,
                    rendered,
                    4,
                ])
                self.assertNotIn("$1", conn.cur.sql)
        finally:
            retrieve_mod._connect = original

    def test_two_hydrated_hits_stay_on_one_query_and_both_match(self) -> None:
        first = "The gauge at Altenahr rose."
        second = "Paiporta recorded 140 mm in six hours."
        self.assertNotIn("140 mm", first)
        hits = (
            ("kept", first, 1),
            ("other", second, 2),
        )
        rows = [_hit_row(chunk_id, text, page) for chunk_id, text, page in hits]
        result = retrieve_docs(
            "rainfall",
            2,
            {"event_id": "EMSR773"},
            embedder=lambda texts, input_type: [[0.1] * 2048],
            search=lambda vector, event_id, k: [(row["chunk_id"], 0.1) for row in rows],
            hydrate=lambda ids: ("qid", rows),
        )
        self.assertEqual([item["query_id"] for item in result.citations], ["qid", "qid"])
        claims = [
            Claim(
                claim_id="C1",
                text="Altenahr rose.",
                citations=[
                    Citation(
                        citation_id="C1-a1", claim_id="C1", layer="a", query_id="q-sql"
                    )
                ],
            )
        ]
        claims, doc_evidence = _attach_documents(
            claims, result.citations, {"doc_claim_id": "C1"}, "rainfall"
        )
        self.assertEqual(len(doc_evidence), 1)
        self.assertEqual(
            [row["chunk_id"] for row in doc_evidence[0].rows_sample], ["kept", "other"]
        )
        evidence = {
            "q-sql": Evidence(
                query_id="q-sql",
                view="floodsense_seed.hazard_timeline",
                sql="SELECT 1",
                rows_sample=[{"rain_mm": 1}],
                row_count=1,
                executed_at_utc="2026-10-26T12:00:00Z",
            ),
            "qid": doc_evidence[0],
        }
        self.assertTrue(score_claim(claims[0], evidence, None).citation_faithful)

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

    def test_zetaris_string_columns_still_cite(self) -> None:
        # Zetaris REST hydrates page and paragraph as strings ('3', '1').
        row = _hit_row("kept", "Paiporta recorded 140 mm in six hours.", 3)
        row.update(page="3", paragraph="1")
        result = retrieve_docs(
            "rainfall",
            1,
            {"event_id": "EMSR773"},
            embedder=lambda texts, input_type: [[0.1] * 2048],
            search=lambda vector, event_id, k: [("kept", 0.1)],
            hydrate=lambda ids: ("qid", [row]),
        )
        self.assertEqual(len(result.citations), 1)
        self.assertEqual(result.citations[0]["locator"]["page"], 3)
        self.assertEqual(result.citations[0]["locator"]["paragraph"], 1)
        row.update(page="0")
        self.assertEqual(
            retrieve_docs(
                "rainfall",
                1,
                None,
                embedder=lambda texts, input_type: [[0.1] * 2048],
                search=lambda vector, event_id, k: [("kept", 0.1)],
                hydrate=lambda ids: ("qid", [row]),
            ).citations,
            [],
        )

    def test_the_run_request_keeps_doc_query(self) -> None:
        # The runtime hands req.model_dump() to the graph; a dropped field never retrieves.
        req = RunRequest(question="Why Paiporta?", doc_query="Barranc del Poyo discharge")
        self.assertEqual(req.model_dump()["doc_query"], "Barranc del Poyo discharge")
        self.assertIsNone(RunRequest(question="q").model_dump()["doc_query"])


def _hit_row(chunk_id: str, text: str, page: int) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "title": "HESS",
        "source_url": "https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf",
        "publisher": "Copernicus Publications",
        "licence": "CC-BY-4.0",
        "attribution": "Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0",
        "page": page,
        "paragraph": 1,
        "lines": "1-1",
        "section": None,
    }


def _bound_values(sql: str, params: object) -> list:
    """Values in placeholder order. A short tuple against a reused $n fails here."""
    names = re.findall(r"%\((\w+)\)s", sql)
    bare = re.sub(r"%\(\w+\)s", "", sql)
    if names:
        if not isinstance(params, dict):
            raise AssertionError(params)
        return [params[name] for name in names]
    slots = bare.count("%s")
    if not isinstance(params, (tuple, list)) or slots != len(params):
        raise AssertionError(f"{slots} placeholders, {params!r}")
    return list(params)


if __name__ == "__main__":
    unittest.main()
