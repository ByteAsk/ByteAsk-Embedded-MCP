"""SampleBackend and load_backend tests."""

import pytest

from byteask_embedded_mcp.backend import SampleBackend, SearchBackend, load_backend


def test_sample_backend_is_a_searchbackend():
    assert isinstance(SampleBackend(), SearchBackend)


def test_search_hit():
    res = SampleBackend().search("modbus function code 0x10")
    assert res["status"] == "ok"
    assert res["count"] >= 1
    top = res["results"][0]
    assert top["result_id"] == "sample:modbus-fc16"
    assert {"result_id", "doc_title", "section", "page", "page_end", "snippet"} <= top.keys()


def test_search_no_match():
    res = SampleBackend().search("quarterly marketing budget")
    assert res["status"] == "no_match"
    assert res["results"] == []


def test_search_respects_limit():
    res = SampleBackend().search("register", limit=1)
    assert len(res["results"]) <= 1


def test_get_context_roundtrip():
    backend = SampleBackend()
    rid = backend.search("systick register")["results"][0]["result_id"]
    ctx = backend.get_context(rid)
    assert ctx["status"] == "ok"
    assert ctx["result_id"] == rid
    assert ctx["text"]


def test_get_context_not_found():
    assert SampleBackend().get_context("nope")["status"] == "not_found"


def test_load_backend_defaults_to_sample():
    class Cfg:
        backend_factory = ""
    assert isinstance(load_backend(Cfg()), SampleBackend)


def test_load_backend_rejects_bad_spec():
    class Cfg:
        backend_factory = "not-a-valid-spec"
    with pytest.raises(ValueError):
        load_backend(Cfg())
