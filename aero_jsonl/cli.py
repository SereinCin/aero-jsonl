"""Command-line interface for aero_jsonl.

Usage:
    aero-jsonl <map|filter> <expr> <input.jsonl> [output.jsonl]
    aero-jsonl <map|filter> <expr> -            # read stdin
    aero-jsonl <map|filter> <expr> in.jsonl -   # write stdout

``map``   projects each line through the JMESPath expression and writes the
          serialized result (null results are dropped).
``filter`` keeps the original lines whose expression result is truthy.
"""
import sys

from aero_jsonl import map_lines, filter_lines


def _iter_input(path):
    if path == "-":
        for line in sys.stdin:
            yield line
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line


def _open_output(path):
    if path is None or path == "-":
        return sys.stdout
    return open(path, "w", encoding="utf-8")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) < 3:
        sys.stderr.write(
            "usage: aero-jsonl <map|filter> <expr> <input.jsonl> [output.jsonl]\n"
            "       use '-' for stdin/stdout\n"
        )
        return 2
    mode, expr, in_path = argv[0], argv[1], argv[2]
    out_path = argv[3] if len(argv) > 3 else None
    if mode not in ("map", "filter"):
        sys.stderr.write("mode must be 'map' or 'filter'\n")
        return 2
    out = _open_output(out_path)
    try:
        if mode == "map":
            for line in map_lines(expr, _iter_input(in_path)):
                out.write(line + "\n")
        else:
            for line in filter_lines(expr, _iter_input(in_path)):
                out.write(line + "\n")
    finally:
        if out is not sys.stdout:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
