"""리포트 채점 — 숫자 대조·판정 일치·LLM 작성 절·판정자 묶음."""

from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    extract_numbers,
    judge_packets,
    llm_sections,
    unmatched_numbers,
    verdict_matches,
)


def test_숫자_추출은_단위와_쉼표를_정규화하고_작은_정수와_연도는_무시():
    got = dict(extract_numbers("폐업률 12.3%, 점포 1,234곳, 매출 3억, 2024년 기준 3가지"))
    assert got == {"12.3%": 12.3, "1,234": 1234.0, "3억": 3e8}


def test_비율은_퍼센트로_반올림해_맞춘다():
    facts = {"closure_rate": 0.1234, "stores": 1234, "sales": 300000000}
    assert unmatched_numbers("폐업률 12.3%, 점포 1,234곳, 매출 3억", facts) == []


def test_facts에_없는_숫자는_걸린다():
    assert unmatched_numbers("폐업률 45.6%", {"closure_rate": 0.1234}) == ["45.6%"]


def test_문자열_안의_숫자도_facts로_본다():
    assert unmatched_numbers("월세 250만", {"note": "평균 월세 250만원"}) == []


def test_소수_단위_토큰은_표시_자릿수로_반올림해_맞춘다():
    assert unmatched_numbers("매출 3.1억", {"sales": 312000000}) == []


def test_판정_일치는_기대_라벨만_있어야():
    v = {"available": True, "verdict_code": "orange"}
    assert verdict_matches("### 판정\n조건부입니다.", v)
    assert not verdict_matches("### 판정\n비추천입니다.", v)
    assert not verdict_matches("### 판정\n조건부지만 비추천에 가깝다", v)


def test_판정_자료가_없으면_단정_라벨이_없어야():
    v = {"available": False}
    assert verdict_matches("### 판정\n판정 보류입니다.", v)
    assert not verdict_matches("### 판정\n경고 없음", v)


def test_폴백과_같은_절은_LLM_작성이_아니다():
    deltas = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n모델이 쓴 글", "funding": ""}
    fallbacks = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n분석 데이터가 부족합니다.", "funding": "x"}
    assert llm_sections(deltas, fallbacks) == {"reasons"}


def test_판정자_묶음은_모델명을_가리고_결정적이다():
    md1, map1 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    md2, map2 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    assert map1 == map2 and set(map1.values()) == {"gemma4:12b", "qwen3.5:4b"}
    assert "gemma4" not in md1 and "qwen" not in md1
