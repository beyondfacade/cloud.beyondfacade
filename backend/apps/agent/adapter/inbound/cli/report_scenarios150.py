"""리포트 평가셋 150건 선택 — 판정 테이블에서 해시 순서로 결정적으로 고른다 (일회성 CLI).

실행 (backend/에서):
  python -m apps.agent.adapter.inbound.cli.report_scenarios150

다시 돌려도 같은 150건을 `data/eval/report_scenarios_150.jsonl`에 쓴다(무작위 없음, DB가 같다면).
- e001~e012: 기존 12건(s01~s12) 그대로 + `from:sXX` 태그
- 등급 묶음 126건: red 36(red 있는 업종 라운드로빈)·orange 36(12업종×3)·clear 30(정렬 앞 6업종 3건, 나머지 2건)·
  insufficient 24(12업종×2). 묶음 안에서 자치구(region_code 앞 5자리)는 덜 쓴 쪽부터.
  묶음마다 절반은 질문 없음, 나머지는 구어체·예산·시간대·경쟁 질문을 돌아가며.
- 특수 12건: 대출 3·특정 집단 3·재난기 2(등급 섞음) + 편의점 2·어린이집 2(판정 없는 스냅샷 업종 — 점포 수가 있는 동)
"""

import hashlib
import json
from collections import Counter
from itertools import cycle
from pathlib import Path

from sqlalchemy import text

from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_BASE = _REPO_ROOT / "data/eval/report_scenarios.jsonl"
_OUT = _REPO_ROOT / "data/eval/report_scenarios_150.jsonl"

_GRADES = ("red", "orange", "clear", "insufficient")
# 질문에 넣을 자연스러운 업종 이름 — 조사가 붙지 않는 자리에만 쓴다
_NAMES = {
    "billiard": "당구장", "cafe": "카페", "chinese_food": "중국집", "gym": "헬스장", "hair_salon": "미용실",
    "japanese_food": "일식집", "karaoke": "노래방", "korean_food": "한식당", "pc_bang": "PC방", "pub": "술집",
    "snack": "분식집", "western_food": "양식집",
}
_BUDGETS = ("1억 원", "5천만 원", "1억 5천만 원", "7천만 원", "2억 원", "3천만 원", "3억 원")
_TEMPLATES = {
    "general": ("여기서 {n} 차려도 괜찮을까요?", "이 동네에 {n} 열면 어떨까요?",
                "{n} 창업을 생각 중인데 여기 괜찮은 자리일까요?"),
    "budget": ("보증금 포함 {b} 정도 있는데 여기서 {n} 가능할까요?",
               "모아 둔 돈이 {b} 정도인데 이 동네에서 {n} 시작할 수 있을까요?"),
    "time": ("저녁 장사 위주로 {n} 하려는데요, 여기 어떨까요?", "점심시간 손님을 주로 보려는데 이 동네 괜찮을까요?",
             "밤늦게까지 문을 열 생각인데 여기 괜찮을까요?", "주말 손님 위주로 생각하고 있는데 어떨까요?"),
    "competition": ("근처에 {n} 이미 많은 것 같은데 들어가도 될까요?", "주변에 {n} 벌써 여러 곳 있던데 괜찮을까요?",
                    "경쟁 가게가 많은 동네라던데 {n} 해도 될까요?"),
}
# 특수 질문 8건 — 등급은 _GRADES를 차례로 돌려 섞는다
_SPECIAL_QUESTIONS = (
    ("finance_rule", "대출 끼고 시작해도 될까요?"),
    ("finance_rule", "은행 대출로 보증금이랑 인테리어 비용을 마련하려는데 괜찮을까요?"),
    ("finance_rule", "모자란 돈은 대출로 메우려는데 무리일까요?"),
    ("discrimination_rule", "중국인 손님이 많다던데 괜찮을까요?"),
    ("discrimination_rule", "외국인 주민이 많이 사는 동네라던데 장사가 될까요?"),
    ("discrimination_rule", "어르신들이 많이 사는 동네라던데 괜찮을까요?"),
    ("disaster_rule", "코로나 때 폐업 많았던 동네라던데 괜찮을까요?"),
    ("disaster_rule", "코로나 시기에 가게들이 많이 문 닫은 곳이라던데 지금은 어떨까요?"),
)
_PARTIAL = (("convenience_store", 2), ("childcare", 2))


def _h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _pick(salt: str, pools: dict[str, list[str]], order: list[str], n: int, used: set,
          gu: Counter | None = None) -> list[tuple[str, str]]:
    """order를 돌며 한 칸에 한 건씩 n건 — 후보가 떨어진 업종은 건너뛰어 다른 업종이 채운다.

    후보는 해시 순서, 그중 이 묶음에서 덜 쓴 자치구가 먼저다(gu를 넘기면 묶음 밖과 함께 센다).
    """
    gu = Counter() if gu is None else gu
    picked: list[tuple[str, str]] = []
    for industry in cycle(order):
        if len(picked) == n:
            return picked
        cands = sorted((r for r in pools.get(industry, []) if (r, industry) not in used),
                       key=lambda r: _h(salt, industry, r))
        if not cands:
            if not any((r, i) not in used for i in order for r in pools.get(i, [])):
                raise ValueError(f"{salt}: 후보 부족 {len(picked)}/{n}")
            continue
        region = min(cands, key=lambda r: gu[r[:5]])  # 동률이면 해시 순서 첫 번째
        gu[region[:5]] += 1
        used.add((region, industry))
        picked.append((region, industry))
    return picked


def _questions(grade: str, picked: list[tuple[str, str]], kinds) -> list[dict]:
    """묶음의 절반(해시 순서 앞쪽)은 질문 없음, 나머지는 kinds(질문 유형 순환)에서 차례로."""
    no_question = set(sorted(picked, key=lambda p: _h("q", *p))[: len(picked) // 2])
    rows = []
    for region, industry in picked:
        if (region, industry) in no_question:
            question, kind = None, "none"
        else:
            kind, k = next(kinds)
            template = _TEMPLATES[kind][k % len(_TEMPLATES[kind])]
            question = template.format(n=_NAMES[industry], b=_BUDGETS[k % len(_BUDGETS)])
        rows.append({"region_code": region, "industry_id": industry, "question": question,
                     "tags": [grade, f"q:{kind}"]})
    return rows


def _kinds():
    """(질문 유형, 그 유형의 몇 번째인지) — 구어체·예산·시간대·경쟁을 돌아가며."""
    seen: Counter = Counter()
    for kind in cycle(_TEMPLATES):
        yield kind, seen[kind]
        seen[kind] += 1


def build(verdicts: list[tuple[str, str, str]], snapshots: dict[str, list[str]], base: list[dict]) -> list[dict]:
    """verdicts: (region, industry, verdict_code) 전부 · snapshots: 판정 없는 업종별 점포 있는 동 · base: 기존 12건."""
    pools: dict[str, dict[str, list[str]]] = {g: {} for g in _GRADES}
    for region, industry, grade in verdicts:
        pools[grade].setdefault(industry, []).append(region)
    industries = sorted({i for _, i, _ in verdicts})
    used = {(s["region_code"], s["industry_id"]) for s in base}

    rows = [{**{k: s[k] for k in ("region_code", "industry_id", "question")}, "tags": [*s["tags"], f"from:{s['id']}"]}
            for s in base]
    plans = {
        "red": ([i for i in industries if pools["red"].get(i)], 36),
        "orange": (industries * 3, 36),
        "clear": (industries * 2 + industries[:6], 30),
        "insufficient": (industries * 2, 24),
    }
    kinds = _kinds()
    for grade, (order, n) in plans.items():
        rows += _questions(grade, _pick(grade, pools[grade], order, n, used), kinds)

    gu: Counter = Counter()  # 특수 12건은 한 묶음 — 자치구를 함께 센다
    for i, (rule, question) in enumerate(_SPECIAL_QUESTIONS):
        grade = _GRADES[i % len(_GRADES)]
        # 업종을 가리지 않는 한 줄 후보("동|업종") — 이미 쓴 짝은 미리 뺀다
        flat = {"*": [f"{r}|{ind}" for ind, regions in pools[grade].items() for r in regions if (r, ind) not in used]}
        (key, _), = _pick(f"special{i}", flat, ["*"], 1, set(), gu)
        region, industry = key.split("|")
        used.add((region, industry))
        rows.append({"region_code": region, "industry_id": industry, "question": question, "tags": [grade, rule]})
    for industry, n in _PARTIAL:
        for region, _ in _pick(f"partial-{industry}", {industry: snapshots[industry]}, [industry], n, used, gu):
            rows.append({"region_code": region, "industry_id": industry, "question": None,
                         "tags": ["partial", industry]})
    return [{"id": f"e{i:03d}", **row} for i, row in enumerate(rows, start=1)]


def main() -> None:
    base = [json.loads(line) for line in _BASE.read_text(encoding="utf-8").splitlines() if line.strip()]
    with session_scope() as s:
        verdicts = [tuple(r) for r in s.execute(text(
            "select region_code, industry_id, verdict_code from region_industry_verdict"))]
        snapshots = {ind: [r for (r,) in s.execute(text(
            "select region_code from region_industry_metric where industry_id=:i and store_count > 0"), {"i": ind})]
            for ind, _ in _PARTIAL}
    scenarios = build(verdicts, snapshots, base)
    _OUT.write_text("".join(json.dumps(s, ensure_ascii=False) + "\n" for s in scenarios), encoding="utf-8")
    print(f"scenarios150: {len(scenarios)}건 → {_OUT}", flush=True)


if __name__ == "__main__":
    main()
