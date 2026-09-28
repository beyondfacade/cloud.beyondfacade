"""일반음식점 인허가 파일럿 수집 — DB 미적재, JSONL 파일로만 저장.

설계서 docs/superpowers/specs/2026-09-28-industry-expansion-design.md §5 0단계.
실행: cd backend && set -a && . ./.env && set +a && .venv/bin/python ../scripts/pilot_general_restaurants.py [--authority 3220000]
출력: data/raw/mois_permit/general_restaurants_{authority}.jsonl
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

BASE = "https://apis.data.go.kr/1741000/general_restaurants/info"
PAGE = 100
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "mois_permit"


def get_with_retry(client: httpx.Client, params: dict, attempts: int = 4) -> dict:
    for attempt in range(attempts):
        try:
            r = client.get(BASE, params=params)
            r.raise_for_status()
            return r.json()["response"]["body"]
        except (httpx.HTTPStatusError, httpx.TimeoutException, KeyError, ValueError) as e:
            if attempt == attempts - 1:
                raise
            print(f"retry {attempt + 1}: {e}", file=sys.stderr, flush=True)
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority", default="3220000", help="개방자치단체코드 (기본 강남구)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"general_restaurants_{args.authority}.jsonl"
    params = {
        "serviceKey": os.environ["DATA_GO_KR_API_KEY"],
        "numOfRows": PAGE,
        "returnType": "json",
        "cond[OPN_ATMY_GRP_CD::EQ]": args.authority,
    }
    started = time.time()
    written = 0
    with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client, open(out, "w", encoding="utf-8") as f:
        page = 1
        total = None
        while True:
            body = get_with_retry(client, {**params, "pageNo": page})
            total = int(body.get("totalCount") or 0)
            items = (body.get("items") or {}).get("item") or []
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
            written += len(items)
            if page % 25 == 0 or page * PAGE >= total:
                print(f"page {page} — {written}/{total} ({time.time() - started:.0f}s)", flush=True)
            if page * PAGE >= total or not items:
                break
            page += 1
    print(f"done: {written} rows → {out} ({time.time() - started:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
