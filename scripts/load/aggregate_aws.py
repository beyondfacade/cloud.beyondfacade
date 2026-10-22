"""AWS 부하 테스트(11차~) 계단별 집계 — 유지 3분 구간마다 RPS·지연·API별 p95·임베딩 체크·RDS CPU·Ollama.

    python3 scripts/load/aggregate_aws.py logs/load/<단계 폴더>

계단은 meta.txt의 profile로 고른다(load.js STAGES와 같아야 한다 — 계단마다 2분 오르막 + 3분 유지).
폴더에 ollama.csv(ollama_monitor.sh)가 있으면 같은 구간의 임베딩 건/초·GPU 사용률도 붙인다.
"""
import csv
import datetime as dt
import gzip
import json
import re
import sys
from collections import defaultdict

LEVELS = {
    "ceiling3k": [200, 500, 1000, 1500, 2000, 2500, 3000],
    "ceiling4k5": [1000, 2000, 3000, 3500, 4000, 4500],
}
EMBED_CHECK = "검색 가능(임베딩 성공)"

run = sys.argv[1].rstrip("/")
profile = re.search(r"profile=(\S+)", open(f"{run}/meta.txt").read()).group(1)
levels = LEVELS[profile]


def pct(v, p):
    if not v:
        return float("nan")
    v.sort()
    return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


t0 = None
dur = defaultdict(list)
api = defaultdict(lambda: defaultdict(list))
reqs = defaultdict(int)
fails = defaultdict(int)
chk = defaultdict(lambda: [0, 0])
with gzip.open(f"{run}/k6/raw.csv.gz", "rt") as f:
    r = csv.reader(f)
    idx = {k: i for i, k in enumerate(next(r))}
    for row in r:
        ts = int(row[idx["timestamp"]])
        t0 = t0 or ts
        off = ts - t0
        k = (off - 120) // 300
        if k < 0 or k >= len(levels) or (off - 120) % 300 >= 180:
            continue
        metric = row[idx["metric_name"]]
        if metric == "http_reqs":
            reqs[k] += 1
        elif metric == "http_req_failed" and row[idx["metric_value"]].startswith("1"):
            fails[k] += 1
        elif metric == "http_req_duration":
            tags = dict(x.split("=", 1) for x in row[idx["extra_tags"]].split("&") if "=" in x)
            name = tags.get("api", "?")
            v = float(row[idx["metric_value"]])
            api[k][name].append(v)
            if name != "analysis_stream":
                dur[k].append(v)
        elif metric == "checks" and row[idx["check"]] == EMBED_CHECK:
            chk[k][0] += row[idx["metric_value"]].startswith("1")
            chk[k][1] += 1

rds = {}
for res in json.load(open(f"{run}/cloudwatch.json"))["MetricDataResults"]:
    if res["Id"] == "db_cpu":
        for t, v in zip(res["Timestamps"], res["Values"]):
            rds[dt.datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()] = v

ollama = []  # (epoch, 200 수, GPU 사용률)
try:
    day = dt.datetime.fromtimestamp(t0).date()
    for row in csv.DictReader(open(f"{run}/ollama.csv")):
        at = dt.datetime.combine(day, dt.time.fromisoformat(row["time"])).timestamp()
        ollama.append((at, int(row.get("embed_200") or 0), row.get("gpu_util_pct") or ""))
except FileNotFoundError:
    pass

print(f"{run} · profile={profile}")
print("VU | RPS | p50 | p95 | p99 | 검색 외 가장 느린 p95 | 검색 p95 | 임베딩 성공 | 실패 | RDS CPU | Ollama 성공/초 | GPU %")
for k, vu in enumerate(levels):
    if not reqs[k]:
        continue
    w0, w1 = t0 + 120 + k * 300, t0 + 300 + k * 300
    ap = {a: pct(v, 95) for a, v in api[k].items() if a not in ("analysis_stream", "intent")}
    worst = max((a for a in ap if a != "search"), key=ap.get)
    ok, n = chk[k]
    cpu = [v for t, v in rds.items() if w0 - 30 <= t <= w1]
    win = [o for o in ollama if w0 <= o[0] <= w1]
    emb = f"{sum(o[1] for o in win) / (15 * len(win)):.1f}" if win else "-"
    gpu = [float(o[2]) for o in win if o[2]]
    print(f"{vu} | {reqs[k] / 180:.0f} | {pct(dur[k], 50):.0f} | {pct(dur[k], 95):.0f} | {pct(dur[k], 99):.0f} | "
          f"{worst} {ap[worst]:.0f} | {ap.get('search', float('nan')):.0f} | "
          f"{ok}/{n} ({ok / n * 100 if n else 0:.0f}%) | {fails[k]} | {max(cpu) if cpu else float('nan'):.0f}% | "
          f"{emb} | {f'{max(gpu):.0f}' if gpu else '-'}")
