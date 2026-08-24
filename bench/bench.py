# Benchmark aero-jsonl vs pure-Python json and Polars scan_ndjson.
#
# Workload: a realistic agent conversation log (nested messages, reasoning,
# tool calls, long strings). Two operations:
#   map    - extract a deeply nested field per line
#   filter - keep lines matching a condition
#
# Contenders (all produce the full result, output discarded):
#   aero file : aero_jsonl.map_file / filter_file (chunked, arena reset)
#   python    : json.loads per line
#   polars    : pl.scan_ndjson(...).collect(engine="streaming")
#
# Usage:  N=1000000 python bench/bench.py
import json
import os
import sys
import threading
import time

BASE = os.path.dirname(__file__)
ROOT = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)
import aero_jsonl  # noqa: E402
import psutil  # noqa: E402

try:
    import polars as pl
    HAS_POLARS = True
except ImportError:
    HAS_POLARS = False

N = int(os.environ.get("N", "200000"))
PATH = os.path.join(BASE, "data_%d.jsonl" % N)
MAP_EXPR = "messages[1].tool_calls[0].name"
FILT_EXPR = "user == `user-1`"

_BLURB = ("I need you to look at the failing test in src/workers, trace the "
          "exception back to the batch scheduler, and propose a fix that does "
          "not change the public API. Attach the relevant stack frame.")


def build():
    if os.path.exists(PATH):
        return
    with open(PATH, "w") as f:
        for i in range(N):
            f.write(
                '{"ts":%d,"session":"sess-%d","user":"user-%d",'
                '"messages":[{"role":"user","content":"%s"},'
                '{"role":"assistant","content":"Here is my plan: %s",'
                '"reasoning":"First analyse, then propose. %s",'
                '"tool_calls":[{"name":"read_file","args":{"path":"/tmp/f.json"},'
                '"result":"line 42: assertion failed"}]}]}\n'
                % (i, i, i % 100, _BLURB, _BLURB[:120], _BLURB[:80])
            )


class PeakMem:
    def __init__(self):
        self.p = psutil.Process()
        self.peak = 0
        self._stop = False
        self.t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop:
            rss = self.p.memory_info().rss
            if rss > self.peak:
                self.peak = rss
            time.sleep(0.005)

    def __enter__(self):
        self.base = self.p.memory_info().rss
        self.peak = self.base
        self.t.start()
        return self

    def __exit__(self, *a):
        self._stop = True
        self.t.join()


def bench(fn, reps=3):
    times = []
    peaks = []
    for _ in range(reps):
        with PeakMem() as pm:
            t0 = time.perf_counter()
            fn()
            dt = time.perf_counter() - t0
        times.append(dt)
        peaks.append(pm.peak - pm.base)
    times.sort()
    return times[len(times) // 2], max(peaks)


def fmt(dt, mb):
    return "%8.0f ms   %7.1f MB" % (dt * 1000, mb / 1e6)


def python_map(expr, path):
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = json.loads(line)
            v = m["messages"][1]["tool_calls"][0]["name"]
            n += 1
    return n


def python_filter(path):
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if json.loads(line)["user"] == "user-1":
                n += 1
    return n


def main():
    build()
    print("rows=%d  file=%.1f MB  (agent conversation log, nested)\n" % (N, os.path.getsize(PATH) / 1e6))

    print("=== map: extract messages[1].tool_calls[0].name ===")
    rows = []
    aero_dt, aero_m = bench(lambda: aero_jsonl.map_file(MAP_EXPR, PATH, os.devnull))
    py_dt, py_m = bench(lambda: python_map(MAP_EXPR, PATH))
    rows.append(("aero-jsonl", aero_dt, aero_m))
    rows.append(("python json", py_dt, py_m))
    if HAS_POLARS:
        pl_dt, pl_m = bench(lambda: pl.scan_ndjson(PATH)
                            .select(pl.col("messages").list.get(1).struct.field("tool_calls").list.get(0).struct.field("name"))
                            .collect(engine="streaming"))
        rows.append(("polars", pl_dt, pl_m))
    for name, dt, m in rows:
        print("  %-12s %s" % (name, fmt(dt, m)))

    print("\n=== filter: keep user == `user-1` ===")
    rows = []
    aero_dt, aero_m = bench(lambda: aero_jsonl.filter_file(FILT_EXPR, PATH, os.devnull))
    py_dt, py_m = bench(lambda: python_filter(PATH))
    rows.append(("aero-jsonl", aero_dt, aero_m))
    rows.append(("python json", py_dt, py_m))
    if HAS_POLARS:
        pl_dt, pl_m = bench(lambda: pl.scan_ndjson(PATH)
                            .filter(pl.col("user") == "user-1")
                            .collect(engine="streaming"))
        rows.append(("polars", pl_dt, pl_m))
    for name, dt, m in rows:
        print("  %-12s %s" % (name, fmt(dt, m)))


if __name__ == "__main__":
    main()
