# aero-jsonl kernel smoke tests: map / filter / per-line truthy.
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import kernel

PASS = 0
FAIL = 0


def check(name, got, expected):
    global PASS, FAIL
    if isinstance(got, bytes):
        got = got.decode("utf-8", "replace")
    ok = got == expected
    if ok:
        PASS += 1
        print("ok   %-28s" % name)
    else:
        FAIL += 1
        print("FAIL %-28s got=%r expected=%r" % (name, got, expected))


DOC = (
    '{"name":"x","up":true,"load":0.3}\n'
    '{"name":"y","up":false,"load":0.7}\n'
    '{"name":"z","up":true,"load":0.5}\n'
)

# map: project a field; null results are skipped
check("map name", kernel.map_jsonl("name", DOC),
      '"x"\n"y"\n"z"\n')
check("map up", kernel.map_jsonl("up", DOC),
      "true\nfalse\ntrue\n")
# map with nested expression
check("map load > 0.4", kernel.map_jsonl("load > `0.4`", DOC),
      "false\ntrue\ntrue\n")
# map non-object line / null root should skip nothing relevant here
check("map @", kernel.map_jsonl("@", DOC), DOC)

# filter: keep lines whose expression is truthy
check("filter up==true", kernel.filter_jsonl("up == `true`", DOC),
      '{"name":"x","up":true,"load":0.3}\n'
      '{"name":"z","up":true,"load":0.5}\n')
check("filter load<0.6", kernel.filter_jsonl("load < `0.6`", DOC),
      '{"name":"x","up":true,"load":0.3}\n'
      '{"name":"z","up":true,"load":0.5}\n')

# line_truthy: per-line streaming predicate
check("line_truthy y", kernel.line_truthy("up", '{"name":"y","up":false}'), 0)
check("line_truthy x", kernel.line_truthy("up", '{"name":"x","up":true}'), 1)
check("line_truthy missing", kernel.line_truthy("up", '{"name":"a"}'), 0)
check("line_truthy bad line", kernel.line_truthy("up", "not json"), -1)
check("line_truthy bad expr", kernel.line_truthy("foo[", "{}"), -1)

# search still works (single document)
check("search a.b", kernel.search("a.b", '{"a":{"b":"x"}}'), '"x"')

# error handling: bad expression -> \x1eERR1
check("map bad expr", kernel.map_jsonl("foo[", DOC), "\x1eERR1")
check("filter bad expr", kernel.filter_jsonl("foo[", DOC), "\x1eERR1")

# empty doc
check("map empty", kernel.map_jsonl("name", ""), "")
check("filter empty", kernel.filter_jsonl("up", ""), "")

print("\nPASS=%d FAIL=%d" % (PASS, FAIL))
sys.exit(0 if FAIL == 0 else 1)
