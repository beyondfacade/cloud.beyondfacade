"""일반음식점 파일럿 JSONL 분석 — 컬럼 채움률·업태 분포·영업상태·좌표·개업연도·'기타' 상호 표본.

실행: python scripts/pilot_analyze_general_restaurants.py data/raw/mois_permit/general_restaurants_3220000.jsonl
"""

import collections
import json
import sys

path = sys.argv[1]
rows = [json.loads(line) for line in open(path, encoding="utf-8")]
n = len(rows)
print(f"총 {n:,}건\n")

print("== 컬럼 채움률 (비어있지 않은 비율) ==")
cols = sorted({k for r in rows for k in r})
for c in cols:
    filled = sum(1 for r in rows if (r.get(c) or "").strip())
    sample = next(((r.get(c) or "").strip() for r in rows if (r.get(c) or "").strip()), "")
    print(f"{c:28s} {filled / n * 100:6.1f}%  예: {sample[:30]}")

print("\n== 업태구분명 (BZSTAT_SE_NM) 전체 ==")
bz = collections.Counter((r.get("BZSTAT_SE_NM") or "").strip() or "(빈값)" for r in rows)
for k, v in bz.most_common():
    print(f"{k:28s} {v:7,} ({v / n * 100:5.1f}%)")

print("\n== 업태 × 영업상태 ==")
st = collections.Counter(((r.get("BZSTAT_SE_NM") or "").strip() or "(빈값)", (r.get("DTL_SALS_STTS_NM") or "").strip()) for r in rows)
for (b, s), v in sorted(st.items(), key=lambda x: -x[1])[:25]:
    print(f"{b:28s} {s:10s} {v:7,}")

print("\n== 영업상태 (DTL_SALS_STTS_NM) ==")
for k, v in collections.Counter((r.get("DTL_SALS_STTS_NM") or "").strip() for r in rows).most_common():
    print(f"{k:12s} {v:7,}")

print("\n== 좌표 보유율 ==")
has_xy = sum(1 for r in rows if (r.get("CRD_INFO_X") or "").strip() and (r.get("CRD_INFO_Y") or "").strip())
print(f"좌표 있음 {has_xy:,} / {n:,} ({has_xy / n * 100:.1f}%)")
open_rows = [r for r in rows if not (r.get("CLSBIZ_YMD") or "").strip()]
has_xy_open = sum(1 for r in open_rows if (r.get("CRD_INFO_X") or "").strip())
print(f"영업중(폐업일 없음) {len(open_rows):,} 중 좌표 있음 {has_xy_open:,} ({has_xy_open / max(len(open_rows), 1) * 100:.1f}%)")

print("\n== 인허가 연도 분포 (LCPMT_YMD) ==")
yr = collections.Counter((r.get("LCPMT_YMD") or "")[:4] or "(빈값)" for r in rows)
for k in sorted(yr):
    if k >= "2015" or k == "(빈값)":
        print(f"{k} {yr[k]:7,}")
print(f"2015 이전 합계 {sum(v for k, v in yr.items() if k < '2015' and k != '(빈값)'):,}")

print("\n== 폐업 연도 분포 (CLSBIZ_YMD) ==")
cy = collections.Counter((r.get("CLSBIZ_YMD") or "")[:4] for r in rows if (r.get("CLSBIZ_YMD") or "").strip())
for k in sorted(cy):
    if k >= "2019":
        print(f"{k} {cy[k]:7,}")

print("\n== '기타' 업태 상호 표본 40건 ==")
others = [r for r in rows if (r.get("BZSTAT_SE_NM") or "").strip() == "기타"]
for r in others[:40]:
    print(" ", (r.get("BPLC_NM") or "").strip(), "|", (r.get("DTL_SALS_STTS_NM") or "").strip(), "|", (r.get("LCPMT_YMD") or "")[:4])

print("\n== 위생업태명(SNTTN_BZSTAT_NM) 분포 — 업태 보조 후보 ==")
for k, v in collections.Counter((r.get("SNTTN_BZSTAT_NM") or "").strip() or "(빈값)" for r in rows).most_common(20):
    print(f"{k:28s} {v:7,}")
