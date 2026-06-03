import json

import pytest

from app.llm.json_utils import parse_json_object


def test_parse_fenced_json():
    raw = '```json\n{"executiveSummary": "ok"}\n```'
    assert parse_json_object(raw)["executiveSummary"] == "ok"


def test_parse_truncated_json_closes_string():
    raw = '{"executiveSummary": "Site shows strong wind'
    parsed = parse_json_object(raw)
    assert parsed["executiveSummary"].startswith("Site shows strong wind")


def test_parse_rejects_non_object():
    with pytest.raises(json.JSONDecodeError):
        parse_json_object("not json at all")
