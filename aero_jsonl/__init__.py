"""aero_jsonl: native JSONL processing for Python.

A thin wrapper around the Aero-compiled JSONL kernel. The heavy lifting —
per-line JSON parsing, JMESPath expression evaluation and serialization —
runs entirely in native code. Usage modes:

* file : ``map_file(expr, in, out)`` / ``filter_file(...)`` process whole
  files in chunks. The expression is parsed once per chunk; the Aero arena is
  reset at every C-extension boundary, so memory stays bounded.
* line : ``map_lines(expr, iterable)`` / ``filter_lines(...)`` iterate one
  line per native call — the lowest-memory mode for arbitrarily large files.
* batch: ``map_jsonl(expr, data)`` / ``filter_jsonl(expr, data)`` operate on
  an in-memory JSONL string (bounded to a few thousand lines per call).
"""
from .kernel import search, map_jsonl, filter_jsonl, line_truthy

__all__ = [
    "search", "map_jsonl", "filter_jsonl", "line_truthy",
    "map_file", "filter_file", "map_lines", "filter_lines",
]
__version__ = "0.1.0"

_ERR = b"\x1eERR"
# The Aero runtime does not reclaim per-line strings inside a single native
# call; chunking bounds each call so the arena is reset regularly.
_CHUNK = 5000


def _is_err(r):
    return isinstance(r, bytes) and r.startswith(_ERR)


def _write_chunk(fout, mode, expr, lines):
    data = "".join(lines)
    if mode == "map":
        r = map_jsonl(expr, data)
        if not _is_err(r):
            fout.write(r.decode("utf-8", "replace"))
    else:
        r = filter_jsonl(expr, data)
        if not _is_err(r):
            fout.write(r.decode("utf-8", "replace"))


def map_file(expr, in_path, out_path, chunk=_CHUNK):
    """Project ``expr`` over every line of ``in_path`` and write the
    serialized results to ``out_path`` (null results are skipped)."""
    _process_file("map", expr, in_path, out_path, chunk)


def filter_file(expr, in_path, out_path, chunk=_CHUNK):
    """Keep the lines of ``in_path`` whose ``expr`` result is truthy and
    write them (unmodified) to ``out_path``."""
    _process_file("filter", expr, in_path, out_path, chunk)


def _process_file(mode, expr, in_path, out_path, chunk):
    buf = []
    with open(in_path, "r", encoding="utf-8", errors="replace") as fin, \
            open(out_path, "w", encoding="utf-8", newline="") as fout:
        for line in fin:
            buf.append(line)
            if len(buf) >= chunk:
                _write_chunk(fout, mode, expr, buf)
                buf = []
        if buf:
            _write_chunk(fout, mode, expr, buf)


def map_lines(expr, lines):
    """Project ``expr`` over an iterable of JSON lines, yielding serialized
    results. Lines whose expression evaluates to null are skipped. One native
    call per line — the lowest-memory mode.
    """
    for line in lines:
        line = line.strip()
        if not line:
            continue
        r = search(expr, line)
        if _is_err(r) or r == b"null":
            continue
        yield r.decode("utf-8", "replace")


def filter_lines(expr, lines):
    """Keep the lines whose ``expr`` result is truthy; yields original lines
    (unmodified). One native call per line — the lowest-memory mode.
    """
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line_truthy(expr, line) == 1:
            yield line
