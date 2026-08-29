# aero-jsonl query helpers: where() / extract() over any jsonl source.
#
# These live here, not in the `jsonl` package, so that jsonl stays a
# zero-dependency JSONL I/O library. We use jsonl.load as the source layer
# (file / URL / compressed / file-like) and push each decoded object through
# the native kernel. Results stream, so memory stays bounded.
#
# This is the reverse dependency direction that `jsonl`'s maintainers asked
# for: aero-jsonl depends on jsonl underneath, and the query API stays in
# aero-jsonl.

import json

import jsonl

from .kernel import line_truthy, search


def _compact(obj):
    # Stable, compact serialization of a decoded object back to a single line.
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def where(expr, source, /, **kwargs):
    """Keep the objects of a JSON Lines source whose JMESPath ``expr`` result is truthy.

    Iterates ``jsonl.load`` and evaluates one line per object in the native
    kernel. Results are streamed with bounded memory.

    :param str expr: JMESPath expression (e.g. ``"status == `active`"``).
    :param source: Any source accepted by :func:`jsonl.load`.
    :param Unpack[dict] kwargs: Forwarded to :func:`jsonl.load`.
    :rtype: Iterator[Any]
    """

    for obj in jsonl.load(source, **kwargs):
        if line_truthy(expr, _compact(obj)) == 1:
            yield obj


def extract(expr, source, /, **kwargs):
    """Project a JMESPath ``expr`` over the objects of a JSON Lines source, yielding non-null results.

    Results are decoded values (scalars or nested structures). ``null`` and
    internal errors are skipped.

    :param str expr: JMESPath expression (e.g. ``"messages[1].tool_calls[0].name"``).
    :param source: Any source accepted by :func:`jsonl.load`.
    :param Unpack[dict] kwargs: Forwarded to :func:`jsonl.load`.
    :rtype: Iterator[Any]
    """

    for obj in jsonl.load(source, **kwargs):
        result = search(expr, _compact(obj))
        if result and not result.startswith(b"\x1eERR") and result != b"null":
            yield json.loads(result.decode("utf-8", "replace"))