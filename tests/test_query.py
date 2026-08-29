# aero-jsonl where() / extract() query tests.
#
# These exercise the object-level query helpers that live in aero-jsonl (not
# in `jsonl`). They reuse jsonl.load as the source layer, so file-like and
# compressed sources are covered through jsonl itself.

import gzip
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_pr_pyjsonl"))

import aero_jsonl  # noqa: E402

PASS = 0
FAIL = 0

DOC = (
    '{"name":"x","up":true,"load":0.3}\n'
    '{"name":"y","up":false,"load":0.7}\n'
    '{"name":"z","up":true,"load":0.5}\n'
    '{"name":"w","messages":[{"tool_calls":[{"name":"a"}]},{"tool_calls":[{"name":"b"}]}]}\n'
)


def check(name, got, expected):
    global PASS, FAIL
    ok = got == expected
    if ok:
        PASS += 1
        print("ok   %-28s" % name)
    else:
        FAIL += 1
        print("FAIL %-28s got=%r expected=%r" % (name, got, expected))


def _file(source):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as fd:
        fd.write(source)
        path = fd.name
    return path


def _gz_file(source):
    with tempfile.NamedTemporaryFile(suffix=".jsonl.gz", delete=False) as fd:
        path = fd.name
    with gzip.open(path, "wt", encoding="utf-8") as fd:
        fd.write(source)
    return path


# where: keep objects whose expression is truthy
check("where up==true (file)",
      [o["name"] for o in aero_jsonl.where("up == `true`", _file(DOC))], ["x", "z"])
check("where load>0.4 (file)",
      [o["name"] for o in aero_jsonl.where("load > `0.4`", _file(DOC))], ["y", "z"])
check("where missing field is falsy",
      list(aero_jsonl.where("missing", _file(DOC))), [])

# extract: project a field / nested path, skipping nulls
check("extract name",
      [o for o in aero_jsonl.extract("name", _file(DOC))], ["x", "y", "z", "w"])
check("extract nested tool name",
      [o for o in aero_jsonl.extract("messages[1].tool_calls[0].name", _file(DOC))],
      ["b"])
check("extract null skipped",
      list(aero_jsonl.extract("does_not_exist", _file(DOC))), [])

# source forms
check("where from file-like (StringIO)",
      [o["name"] for o in aero_jsonl.where("up == `true`", io.StringIO(DOC))], ["x", "z"])
check("where from gzip source",
      [o["name"] for o in aero_jsonl.where("up == `true`", _gz_file(DOC))], ["x", "z"])

# edge cases
check("where empty input",
      list(aero_jsonl.where("up == `true`", io.StringIO(""))), [])
check("extract bad expression yields nothing (no crash)",
      list(aero_jsonl.extract("foo[", _file(DOC))), [])

print("\nPASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)