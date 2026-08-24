# aero-jsonl

Native **JSON Lines (JSONL / NDJSON)** processing for Python, written in
[Aero](https://github.com/aero-lang/aero). One JMESPath expression filters or
projects every line of a `.jsonl` / `.ndjson` log — no pandas, no Polars, no
SQL, no Python object round-trip for the hot path.

> **Status:** v0.1 source release. The package will land on PyPI once platform
> wheels are built; for now install from source (see [Build](#build)).

```python
import aero_jsonl

aero_jsonl.filter_file("status == `active`", "app.log.jsonl", "active.jsonl")
aero_jsonl.map_file("messages[1].tool_calls[0].name", "sessions.jsonl", "tools.txt")
```

```bash
aero-jsonl filter "status == `active`" app.log.jsonl active.jsonl
aero-jsonl map "user" sessions.jsonl users.txt
```

## Why

Agent frameworks, LLM training datasets, log aggregators and streaming APIs all
emit JSONL — one JSON object per line. The pain is real and growing: a 12 GB
agent conversation log crashes `json.loads` (it balloons to 25–40 GB of RAM)
and forces you to reach for a heavy dataframe engine or a full database just to
"keep the lines where the level is error".

`aero-jsonl` is the lightweight middle ground:

- **JMESPath expression, not a language.** `"messages[1].tool_calls[0].name"`
  or `"status == `active`"` — the same expression language that powers
  [jmespath.py](https://github.com/jmespath/jmespath.py). No dataframe API to
  learn, no SQL dialect.
- **Streaming with bounded memory.** The Python API iterates/chunks line by
  line and the Aero kernel resets its arena at every native-call boundary, so a
  50 GB file does not need 50 GB of RAM.
- **Zero heavy dependencies.** No pandas/Polars 70 MB wheel, no embedded
  database engine. The kernel is one small Aero-compiled C extension.

## API

| Function | Mode | Description |
|----------|------|-------------|
| `map_file(expr, in, out)` | file | Project `expr` over every line; null results skipped |
| `filter_file(expr, in, out)` | file | Keep lines whose `expr` result is truthy |
| `map_lines(expr, iterable)` | line | Same as `map_file` over an iterable, one native call per line |
| `filter_lines(expr, iterable)` | line | Same as `filter_file` over an iterable |
| `map_jsonl(expr, data)` / `filter_jsonl(expr, data)` | batch | Operate on an in-memory JSONL string (bounded per call) |

Semantics: `map` serializes the expression result per line (null → line
dropped); `filter` keeps the original line when the result is truthy. Both are
the same JMESPath evaluator that passes all 578 official compliance tests.

## Command line

```
aero-jsonl <map|filter> <expr> <input.jsonl> [output.jsonl]
aero-jsonl <map|filter> <expr> -            # read stdin
aero-jsonl <map|filter> <expr> in.jsonl -   # write stdout
```

## Build

Requires the [Aero toolchain](https://github.com/aero-lang/aero). From the repo
root:

```
aero build src/kernel.aero --pyext      # -> src/kernel.pyd / kernel.so
cp src/kernel.pyd aero_jsonl/           # package the extension
```

## Tests

```
python tests/test_jsonl.py     # 16 map/filter/error tests
```

## Benchmark & honest positioning

`bench/bench.py` measures a 137 MB / 200k-line agent conversation log
(nested `messages`, long strings). Median of 3, Windows 11 / Python 3.12:

```
=== map: extract messages[1].tool_calls[0].name ===
  aero-jsonl      874 ms
  python json     688 ms
  polars          242 ms

=== filter: keep user == `user-1` ===
  aero-jsonl     1134 ms
  python json     661 ms
  polars          251 ms
```

Positioning, honestly stated:

- **Speed:** `aero-jsonl` v0.1 is *on par with* pure-Python `json.loads` and
  slower than Polars' columnar `scan_ndjson`. If your workload is tabular rows
  and you already accept a dataframe dependency, Polars is the right tool.
- **Where aero-jsonl wins:** no dataframe dependency, no SQL to learn, a single
  JMESPath expression for both extraction and filtering, and bounded-memory
  streaming for very large files where `json.loads` runs out of RAM.
- **Roadmap:** the kernel is a straightforward Aero port; closing the gap to
  CPython/Rust-level parse throughput (avoiding per-line string copies) is the
  next optimization target.

## License

MIT
