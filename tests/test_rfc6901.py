"""Ground truth from RFC 6901 (JSON Pointer), read from the copy saved by fetch_upstream.

The RFC is not part of the repository (see tests/upstream/MANIFEST.json); these tests
skip while it is absent. Its section 5 and 6 examples give a document and the value
each pointer selects; every pointer is decoded here as the RFC says (``~1`` then
``~0``) and the result must equal what dotreach reads at the same keys.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

import pytest
from conftest import upstream

import dotreach as d

RFC = "rfc6901.txt"
_PAGE_BREAK = re.compile(
    r"\n+\f?\n*Bryan, et al\. +Standards Track +\[Page \d+\]\n\f?\nRFC 6901.*\n"
)


def _text() -> str:
    return _PAGE_BREAK.sub("\n", upstream(RFC))


def _document() -> Any:
    text = _text()
    body = text[text.index("given the JSON document") :]
    return json.loads(body[body.index("{") : body.index("The following JSON strings")])


def _rows(start: str, end: str) -> list[str]:
    text = _text()
    body = text[text.index(start) :]
    return [row.strip() for row in body[: body.index(end)].splitlines()[1:] if row.strip()]


def _tokens(pointer: str) -> list[str]:
    return [t.replace("~1", "/").replace("~0", "~") for t in pointer.split("/")[1:]]


def _cases() -> list[tuple[list[str], Any]]:
    cases = []
    for row in _rows("evaluate to the accompanying values:", "6.  URI Fragment"):
        pointer, end = json.JSONDecoder().raw_decode(row)
        value = row[end:].strip()
        if not value.startswith("//"):
            cases.append((_tokens(pointer), json.loads(value)))
    for row in _rows("identifiers evaluate to the accompanying values:", "7.  Error"):
        fragment, value = row.split(maxsplit=1)
        if not value.startswith("//"):
            cases.append((_tokens(urllib.parse.unquote(fragment[1:])), json.loads(value)))
    return cases


def test_the_rfc_example_has_eleven_pointers_in_each_form() -> None:
    assert len(_cases()) == 22  # 11 per table, the whole-document pointer left out


def test_every_rfc_pointer_reads_the_same_value_by_exact_keys() -> None:
    doc = _document()
    for tokens, expected in _cases():
        assert d.get(doc, tokens) == expected, tokens
        assert d.has(doc, tokens)


def test_every_rfc_pointer_reads_the_same_value_as_an_escaped_string_path() -> None:
    doc = _document()
    for tokens, expected in _cases():
        path = d.join_path(tokens, "/")
        if path == "":
            with pytest.raises(d.InvalidPathError):  # one empty key: not a string path
                d.get(doc, path, sep="/", escape=True)
            continue
        assert d.split_path(path, "/") == tokens
        assert d.get(doc, path, sep="/", escape=True) == expected


def test_glob_and_flatten_see_the_rfc_document_as_its_pointers_do() -> None:
    doc = _document()
    flat = d.flatten(doc, sep="/", escape=True)
    for tokens, expected in _cases():
        if not isinstance(expected, list):
            assert flat[d.join_path(tokens, "/")] == expected
    assert flat.pop("") == 0  # a lone empty key flattens to "", which is not a path
    rebuilt = d.unflatten(flat, sep="/", escape=True, create_lists=True)
    assert rebuilt == {key: value for key, value in doc.items() if key != ""}


def test_array_indices_differ_from_the_rfc_only_as_documented() -> None:
    assert "%x30 / ( %x31-39 *(%x30-39) )" in _text()  # the RFC forbids leading zeros
    doc = _document()
    assert d.get(doc, ("foo", "01")) == "baz"  # dotreach reads decimal text as int() does
    assert d.get(doc, ("foo", "-1")) == "baz"  # and counts negative indices from the end
    assert not d.has(doc, ("foo", "-"))  # "-" names no element, as in the RFC
