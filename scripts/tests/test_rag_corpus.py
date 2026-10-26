"""Corpus manifest and fetch-rag-corpus. No network and no embeddings."""

from __future__ import annotations

import hashlib
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rag_corpus  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _entry(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "doc_id": "hess-29-6715-2025",
        "title": "Torrential rainfall in Valencia",
        "publisher": "Copernicus Publications",
        "url": "https://hess.copernicus.org/articles/29/6715/2025/hess-29-6715-2025.pdf",
        "licence": "CC-BY-4.0",
        "attribution": "Rombeek, Hrachowitz, and Uijlenhoet (2025), CC BY 4.0",
        "sha256": "ab" * 32,
        "tier": 2,
        "event_id": "EMSR773",
        "path": "pdf/hess-29-6715-2025.pdf",
        "placement": "git",
    }
    base.update(overrides)
    return base


def _yaml(entries: list[dict[str, object]]) -> str:
    lines = ["# test manifest"]
    for entry in entries:
        first = True
        for key in (
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
        ):
            value = entry[key]
            if value is None:
                rendered = "null"
            elif isinstance(value, int):
                rendered = str(value)
            else:
                rendered = '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'
            if first:
                lines.append(f"- {key}: {rendered}")
                first = False
            else:
                lines.append(f"  {key}: {rendered}")
    return "\n".join(lines) + "\n"


class ParseManifestTest(unittest.TestCase):
    def test_round_trip_fields(self) -> None:
        parsed = rag_corpus.parse_manifest(_yaml([_entry(title='Map: "Horta"')]))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], 'Map: "Horta"')
        self.assertEqual(parsed[0]["tier"], 2)
        self.assertEqual(parsed[0]["event_id"], "EMSR773")

    def test_tier3_may_omit_event(self) -> None:
        parsed = rag_corpus.parse_manifest(
            _yaml(
                [
                    _entry(
                        tier=3,
                        event_id=None,
                        placement="fetch",
                        path="fetched/note.txt",
                    )
                ]
            )
        )
        self.assertIsNone(parsed[0]["event_id"])

    def test_rejects_noncommercial_licence(self) -> None:
        with self.assertRaises(rag_corpus.CorpusError) as caught:
            rag_corpus.parse_manifest(_yaml([_entry(licence="CC-BY-NC-ND-4.0")]))
        self.assertIn("CC-BY-NC-ND-4.0", str(caught.exception))

    def test_rejects_http_url(self) -> None:
        with self.assertRaises(rag_corpus.CorpusError):
            rag_corpus.parse_manifest(_yaml([_entry(url="http://example.com/a.pdf")]))

    def test_rejects_path_escape(self) -> None:
        with self.assertRaises(rag_corpus.CorpusError):
            rag_corpus.parse_manifest(_yaml([_entry(path="pdf/../../secrets.env")]))


class FetchCorpusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write(self, entries: list[dict[str, object]], files: dict[str, bytes] | None = None) -> None:
        corpus = self.root / "corpus"
        corpus.mkdir()
        (corpus / "manifest.yaml").write_text(_yaml(entries), encoding="utf-8")
        for rel, data in (files or {}).items():
            dest = corpus / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    def test_git_file_matches_without_download(self) -> None:
        body = b"%PDF-1.4 git\n"
        digest = hashlib.sha256(body).hexdigest()
        self._write([_entry(sha256=digest)], {"pdf/hess-29-6715-2025.pdf": body})

        def opener(url: str) -> bytes:
            raise AssertionError(url)

        out = io.StringIO()
        with redirect_stdout(out):
            code = rag_corpus.fetch_rag_corpus(self.root, opener=opener)
        self.assertEqual(code, 0)
        self.assertIn("1 checked, 0 fetched", out.getvalue())

    def test_git_mismatch_does_not_download(self) -> None:
        body = b"wrong"
        self._write([_entry()], {"pdf/hess-29-6715-2025.pdf": body})
        calls: list[str] = []

        def opener(url: str) -> bytes:
            calls.append(url)
            return body

        err = io.StringIO()
        with redirect_stderr(err):
            code = rag_corpus.fetch_rag_corpus(self.root, opener=opener)
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])
        self.assertIn("sha256", err.getvalue())

    def test_fetch_writes_under_fetched_and_checks_sha256(self) -> None:
        body = b"bulletin"
        digest = hashlib.sha256(body).hexdigest()
        entry = _entry(
            doc_id="bulletin-1",
            tier=3,
            event_id=None,
            placement="fetch",
            path="fetched/bulletin.txt",
            sha256=digest,
            url="https://example.com/bulletin.txt",
        )
        self._write([entry])

        def opener(url: str) -> bytes:
            self.assertEqual(url, "https://example.com/bulletin.txt")
            return body

        code = rag_corpus.fetch_rag_corpus(self.root, opener=opener)
        dest = self.root / "corpus" / "fetched" / "bulletin.txt"
        self.assertEqual(code, 0)
        self.assertEqual(dest.read_bytes(), body)

    def test_fetch_keeps_a_matching_file(self) -> None:
        body = b"bulletin"
        digest = hashlib.sha256(body).hexdigest()
        entry = _entry(
            doc_id="bulletin-1",
            tier=3,
            event_id=None,
            placement="fetch",
            path="fetched/bulletin.txt",
            sha256=digest,
        )
        self._write([entry], {"fetched/bulletin.txt": body})

        def opener(url: str) -> bytes:
            raise AssertionError(url)

        self.assertEqual(rag_corpus.fetch_rag_corpus(self.root, opener=opener), 0)

    def test_bad_download_hash_is_not_kept(self) -> None:
        entry = _entry(
            doc_id="bulletin-1",
            tier=3,
            event_id=None,
            placement="fetch",
            path="fetched/bulletin.txt",
            sha256="cd" * 32,
            url="https://example.com/bulletin.txt",
        )
        self._write([entry])

        def opener(url: str) -> bytes:
            return b"not-the-file"

        err = io.StringIO()
        with redirect_stderr(err):
            code = rag_corpus.fetch_rag_corpus(self.root, opener=opener)
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "corpus" / "fetched" / "bulletin.txt").exists())
        self.assertIn("sha256", err.getvalue())

    def test_does_not_embed_or_call_docker(self) -> None:
        source = Path(rag_corpus.__file__).read_text(encoding="utf-8")
        self.assertNotIn("integrate.api.nvidia.com", source)
        self.assertNotIn("input_type", source)
        self.assertNotIn("nvapi-", source)
        self.assertNotIn("docker", source)


class CommittedCorpusTest(unittest.TestCase):
    def test_gitignore_keeps_cache_and_fetched_out(self) -> None:
        text = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("corpus/.embed-cache/", text)
        self.assertIn("corpus/fetched/", text)

    def test_committed_files_match_the_manifest(self) -> None:
        def opener(url: str) -> bytes:
            raise AssertionError(url)

        out = io.StringIO()
        with redirect_stdout(out):
            code = rag_corpus.fetch_rag_corpus(ROOT, opener=opener)
        self.assertEqual(code, 0, out.getvalue())
        manifest = rag_corpus.parse_manifest((ROOT / "corpus" / "manifest.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            [row["doc_id"] for row in manifest],
            [
                "emsr773-aoi03-del",
                "emsr517-aoi15-gra",
                "hess-29-6715-2025",
                "nhess-23-1287-2023",
                "easyxlab-s19",
            ],
        )
        self.assertTrue(all(row["placement"] == "git" for row in manifest))
        legal = (ROOT / "docs" / "legal" / "sources.md").read_text(encoding="utf-8")
        for needle in (
            "EMSR517",
            "10.5194/hess-29-6715-2025",
            "10.5194/nhess-23-1287-2023",
            "https://easybyte.es/lab/studies/s19/paper/",
            "CC BY 4.0",
        ):
            self.assertIn(needle, legal)


if __name__ == "__main__":
    unittest.main()
