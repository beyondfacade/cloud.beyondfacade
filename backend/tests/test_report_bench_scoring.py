"""리포트 채점 — 숫자 대조·판정 일치·LLM 작성 절·판정자 묶음."""

from apps.agent.adapter.inbound.cli.report_bench_scoring import (
    extract_numbers,
    judge_packets,
    llm_sections,
    unmatched_numbers,
    classify_violation,
    verdict_matches,
    verdict_states_grade,
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


def test_판정_일치는_다른_등급을_단정할_때만_거짓():
    v = {"available": True, "verdict_code": "orange"}
    assert verdict_matches("### 판정\n조건부입니다.", v)
    assert not verdict_matches("### 판정\n비추천입니다.", v)
    assert not verdict_matches("### 판정\n조건부지만 비추천에 가깝다", v)


def test_판정_자료가_없으면_등급_단정이_없어야():
    v = {"available": False}
    assert verdict_matches("### 판정\n판정 보류입니다.", v)
    assert verdict_matches("판정을 내리지 않습니다", v)
    assert not verdict_matches("### 판정\n경고 없음", v)


def test_실제_출력_표현은_모순이_아니다():
    assert verdict_matches("'주의' 등급입니다", {"available": True, "verdict_code": "orange"})
    assert verdict_matches("`insufficient` 등급으로 판정되었고 `shrinking` 신호 1개가 있다",
                           {"available": True, "verdict_code": "insufficient"})
    assert verdict_matches("`빨간불` 켜진 상권입니다", {"available": True, "verdict_code": "red"})
    assert verdict_matches("두 개의 강력한 위험 신호가 켜져 있습니다", {"available": True, "verdict_code": "red"})
    assert verdict_matches("등급을 알려드릴 수 없습니다 판정을 내리지 않습니다", {"available": False})


def test_판정_없음을_말하면_등급_판정과_모순():
    assert not verdict_matches("**판정 없음**: 자료 부족", {"available": True, "verdict_code": "red"})
    assert not verdict_matches("판정 없음. 판정이 부여되지 않았습니다.", {"available": True, "verdict_code": "clear"})


def test_폴백과_같은_절은_LLM_작성이_아니다():
    deltas = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n모델이 쓴 글", "funding": ""}
    fallbacks = {"verdict": "### 판정\n코드 문구", "reasons": "### 이유\n분석 데이터가 부족합니다.", "funding": "x"}
    assert llm_sections(deltas, fallbacks) == {"reasons"}


def test_판정자_묶음은_모델명을_가리고_결정적이다():
    md1, map1 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    md2, map2 = judge_packets("s01", {"k": 1}, {"gemma4:12b": "글1", "qwen3.5:4b": "글2"}, seed=0)
    assert map1 == map2 and set(map1.values()) == {"gemma4:12b", "qwen3.5:4b"}
    assert "gemma4" not in md1 and "qwen" not in md1


def test_복합_금액은_한_토큰으로_합산해_맞춘다():
    assert unmatched_numbers("보증금 1억 2천만원", {"a": 120_000_000}) == []
    assert unmatched_numbers("보증금 1억2천만원", {"a": 120_000_000}) == []
    assert unmatched_numbers("보증금 1억 2천만원", {"a": 150_000_000}) == ["1억 2천만"]


def test_부호는_보지_않고_퍼센트p도_퍼센트로_본다():
    assert unmatched_numbers("-2.1%p", {"d": -0.021}) == []
    assert unmatched_numbers("2.1%p 감소", {"d": -2.1}) == []


def test_판정_동의어를_인정하고_다른_등급_핵심_라벨은_모순():
    assert verdict_matches("### 판정\n주황 등급입니다", {"available": True, "verdict_code": "orange"})
    assert verdict_matches("경고가 없습니다", {"available": True, "verdict_code": "clear"})
    assert not verdict_matches("조건부지만 비추천에 가깝다", {"available": True, "verdict_code": "orange"})
    assert verdict_matches("판정 없음 — 자료 부족", {"available": False})


def test_연령대와_순위는_사실값이_아니다():
    assert unmatched_numbers("20대 비중이 높고 12위", {}) == []


def test_위반_문장을_유형으로_분류한다():
    assert classify_violation("[확인된 사실]·[참고 신호] 표기를 전혀 하지 않음") == "신뢰 등급 표기"
    assert classify_violation("금리·한도를 언급하면서 '예상치' 고지 없음") == "금융"
    assert classify_violation("재난기(2022) 폐업률 상승을 왜곡") == "재난기"
    assert classify_violation("외국인 손님을 비하") == "차별"
    assert classify_violation("섹션 구분 없음") == "기타"


def test_판정자_묶음_머리는_기준표와_전체_facts_경로를_알리고_요약이_잘렸다고_말한다():
    md, _ = judge_packets("s03", {"k": "x" * 5000}, {"gemma4:12b": "글"}, seed=0)
    assert "data/eval/report_judge_rubric.md" in md and "data/eval/report_facts/s03.json" in md
    assert "앞 3,000자" in md and "x" * 3001 not in md


def test_판정_절에_등급_말이_있는지():
    assert verdict_states_grade("이 조합은 비추천입니다.") is True
    assert verdict_states_grade("판정을 내리지 않습니다.") is True
    assert verdict_states_grade("상권 변화가 큽니다. 신중히 보세요.") is False


# --- 일관성(반복 회차끼리) ---

from apps.agent.adapter.inbound.cli.report_bench_scoring import (  # noqa: E402
    consistency,
    consistency_alt_grades,
    consistency_numbers,
    consistency_outcome,
    consistency_text,
)


def _run(sid="s01", rep=0, verdict="### 판정\n\n신호 2개", alt="- 제과점 (경고 없음)\n- 분식 (조건부)",
         complete=True, verdict_ok=True, unmatched=()):
    return {"id": sid, "rep": rep, "sections": {"verdict": verdict, "alternatives": alt},
            "complete": complete, "verdict_ok": verdict_ok, "unmatched": list(unmatched)}


def test_같은_회차끼리는_일관성이_모두_1이다():
    runs = [_run(rep=r) for r in range(3)]
    assert consistency_outcome(runs) == 1.0
    assert consistency_numbers(runs) == 1.0
    assert consistency_text(runs) == 1.0
    assert consistency_alt_grades(runs) == 1.0


def test_숫자가_하나_다르면_Jaccard로_잰다():
    runs = [_run(rep=0, verdict="폐업률 12.3%, 점포 150곳"), _run(rep=1, verdict="폐업률 12.5%, 점포 150곳")]
    assert consistency_numbers(runs) == 1 / 3  # {12.3, 150} vs {12.5, 150}


def test_결과가_다르면_그_시나리오는_불일치다():
    runs = [_run(rep=0), _run(rep=1, unmatched=["3%"]), _run(sid="s02", rep=0), _run(sid="s02", rep=1)]
    assert consistency_outcome(runs) == 0.5


def test_대안_등급이_다르면_0이다():
    runs = [_run(rep=0), _run(rep=1, alt="- 제과점 (비추천)\n- 분식 (조건부)")]
    assert consistency_alt_grades(runs) == 0.0


def test_본문_유사도는_SequenceMatcher_비율의_평균이다():
    import difflib

    a, b = "### 판정\n\n신호 2개", "### 판정\n\n신호 3개"
    runs = [_run(rep=0, verdict=a, alt=""), _run(rep=1, verdict=b, alt="")]
    assert consistency_text(runs) == difflib.SequenceMatcher(None, a, b).ratio()


def test_회차가_하나뿐인_시나리오는_계산에서_뺀다():
    runs = [_run(sid="s01", rep=0), _run(sid="s02", rep=0), _run(sid="s02", rep=1, unmatched=["x"])]
    assert consistency_outcome(runs) == 0.0  # s02만 센다
    assert consistency([_run(rep=0)]) is None  # 비교할 쌍이 없다
    assert consistency(runs)["scenarios"] == 1


# --- 코드 절 자동 검사·해석 판정 묶음 (v0.68.0 코드 우선 구조) ---


def test_범위_낱말_없이_숫자만_있는_줄을_찾는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import unscoped_number_lines

    markdown = "\n".join([
        "[확인된 사실] 송정동 한식 연간 폐업률: 2019년 2.8% → 2025년 19.1%.",  # 범위 있음
        "영업 중 점포 평균 124개월.",  # 범위 없음
        "- 「2026년 3천만원 지원 공고」 — 중소벤처기업부, 마감 2026-10-07",  # 공고 제목 속 숫자는 세지 않는다
        "- 상계3.4동 (경고 없음)",  # 숫자가 든 동 이름
    ])

    assert unscoped_number_lines(markdown, ["송정동", "한식", "서울"], ["상계3.4동"]) == ["영업 중 점포 평균 124개월."]


def test_자료가_없는데_이유가_적히지_않은_자리를_찾는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import missing_data_gaps

    facts = {
        "hour_gap": {"available": False, "reason": "시간대 자료 없음"},
        "profile": {"available": False, "reason": "프로필 없음"},
        "verdict": {"available": True, "signals": [{"key": "survival_cliff", "level": "unavailable", "evidence": "표본 부족 — 1곳"}]},
    }
    sections = {name: "" for name in ("verdict", "reasons", "analogs", "conditions", "alternatives", "funding")}
    sections["conditions"] = "시간대: 자료 부족 — 시간대 자료 없음"

    assert missing_data_gaps(facts, sections) == ["profile", "signal:survival_cliff"]


def test_해석_판정_묶음은_본문_한_벌과_가린_해석을_싣는다():
    from apps.agent.adapter.inbound.cli.report_bench_scoring import answer_packets

    packet, mapping = answer_packets("e001", None, "### 판정\n\n본문", {"m1": "해석 하나.", "m2": "해석 둘."}, 0)

    assert sorted(mapping.values()) == ["m1", "m2"]
    assert packet.count("### 판정") == 1 and "질문: (없음 — 총평)" in packet
    assert "해석 하나." in packet and "해석 둘." in packet and "m1" not in packet
