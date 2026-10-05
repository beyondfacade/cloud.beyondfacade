"""report_guards — 리포트 출력 코드 가드 순수 로직 (LLM·DB 없음)."""

from apps.agent.domain.services.report_guards import (
    FUNDING_DISCLAIMER,
    LeadingTagGuard,
    ReportGuard,
    UrlStripper,
    contradicts_verdict,
    disclaimer_suffix,
    guard_section,
)

_RED = {"available": True, "verdict_code": "red"}
_ORANGE = {"available": True, "verdict_code": "orange"}
_CLEAR = {"available": True, "verdict_code": "clear"}


def _stream(stripper: UrlStripper, pieces: list[str]) -> str:
    return "".join(stripper.feed(piece) for piece in pieces) + stripper.flush()


def _run(guard: ReportGuard, chunks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    return [*guard.feed(chunks), *guard.close()]


def _joined(chunks: list[tuple[str, str]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for section, text in chunks:
        out[section] = out.get(section, "") + text
    return out


# --- 판정 모순 ---


def test_red인데_판정_없음이라고_쓰면_모순이다():
    assert contradicts_verdict("### 판정\n\n**판정 없음**: 자료 부족", _RED)


def test_clear인데_판정_없음이라고_쓰면_모순이다():
    assert contradicts_verdict("판정 없음. 판정이 부여되지 않았습니다.", _CLEAR)


def test_orange의_주의_등급_표현은_모순이_아니다():
    assert not contradicts_verdict("'주의' 등급입니다", _ORANGE)


def test_등급_말이_없는_해석은_모순이_아니다():
    assert not contradicts_verdict("### 판정\n\n켜진 신호 2개는 이 상권이 버티기 어렵다는 뜻입니다.", _RED)


def test_판정_자료가_없으면_대조하지_않는다():
    assert not contradicts_verdict("비추천입니다", None)
    assert not contradicts_verdict("비추천입니다", {})


def test_판정_불가인데_등급을_단정하면_모순이다():
    assert contradicts_verdict("조건부입니다", {"available": False, "reason": "표본 부족"})
    assert not contradicts_verdict("판정할 수 없습니다 — 표본 부족", {"available": False, "reason": "표본 부족"})


# --- 링크·공고 번호 제거 ---


def test_한_조각_안의_URL을_지운다():
    assert _stream(UrlStripper(), ["원문은 https://www.bizinfo.go.kr/a?b=1 에서 확인"]) == "원문은 에서 확인"


def test_조각_경계에서_잘린_URL도_지운다():
    assert _stream(UrlStripper(), ["원문 ht", "tps://bizinfo.go.kr/x", " 확인"]) == "원문 확인"


def test_www_주소도_지운다():
    assert _stream(UrlStripper(), ["주소 ww", "w.bizinfo.go.kr 참고"]) == "주소 참고"


def test_공고_번호가_조각_경계에서_갈려도_지운다():
    assert _stream(UrlStripper(), ["공고 PBL", "N_0000", "00109574 는 마감"]) == "공고 는 마감"


def test_pblancId_파라미터를_지운다():
    assert _stream(UrlStripper(), ["번호 pblancId=PBLN_000000000109574 참고"]) == "번호 참고"


def test_URL을_지운_빈_괄호도_정리한다():
    assert _stream(UrlStripper(), ["소상공인 정책자금(https://ols.sbiz.or.kr)은 예상치다."]) == (
        "소상공인 정책자금은 예상치다."
    )
    assert _stream(UrlStripper(), ["[원문](https://a.kr/x) 참고"]) == "[원문] 참고"
    assert _stream(UrlStripper(), ["[https://a.kr](https://a.kr) 참고"]) == " 참고"


def test_괄호가_조각_경계에서_갈려도_정리한다():
    assert _stream(UrlStripper(), ["정책자금 (", "https://a.kr", "/x)."]) == "정책자금."


def test_URL_뒤의_한글은_남긴다():
    assert _stream(UrlStripper(), ["https://a.kr/x에서 확인"]) == "에서 확인"


def test_문장_끝_마침표는_URL에_먹히지_않는다():
    assert _stream(UrlStripper(), ["원문 https://a.kr/x."]) == "원문."


def test_flush는_붙들던_꼬리를_내보낸다():
    stripper = UrlStripper()
    assert stripper.feed("카페 h") == "카페"  # `h`는 `https://`의 앞부분일 수 있다 — 앞 공백과 함께 붙든다
    assert stripper.flush() == " h"
    assert stripper.flush() == ""


def test_링크가_없으면_그대로_흘린다():
    assert _stream(UrlStripper(), ["손익분기 900만원.", "\n\n다음 문단"]) == "손익분기 900만원.\n\n다음 문단"


# --- 기본 신뢰 태그 ---


def _tagged(pieces: list[str]) -> str:
    guard = LeadingTagGuard()
    return "".join(guard.feed(piece) for piece in pieces) + guard.flush()


def test_태그가_없으면_본문_앞에_확인된_사실을_붙인다():
    assert _tagged(["### 왜 안 되나\n\n생존 절벽."]) == "### 왜 안 되나\n\n[확인된 사실] 생존 절벽."


def test_LLM이_붙인_태그는_그대로_둔다():
    assert _tagged(["### 왜 안 되나\n\n[참고 신호] 뉴스."]) == "### 왜 안 되나\n\n[참고 신호] 뉴스."
    assert _tagged(["### 판정\n\n[확", "인된 사실] 켜진 신호 2개."]) == "### 판정\n\n[확인된 사실] 켜진 신호 2개."


def test_헤딩_뒤_공백이_조각으로_갈려도_본문_첫_글자에서_판단한다():
    assert _tagged(["### 그래도", " 한다면", "\n", "\n", "시간대 조건"]) == (
        "### 그래도 한다면\n\n[확인된 사실] 시간대 조건"
    )


def test_헤딩이_없으면_첫_글자부터_본문이다():
    assert _tagged(["생존 절벽."]) == "[확인된 사실] 생존 절벽."


def test_본문이_없으면_태그를_붙이지_않는다():
    assert _tagged(["### 판정"]) == "### 판정"


# --- 고지문 ---


def test_고지문이_없으면_덧붙이고_있으면_중복하지_않는다():
    assert disclaimer_suffix("### 대안 업종 지원사업\n\n공고 2건.") == "\n\n" + FUNDING_DISCLAIMER
    assert disclaimer_suffix("공고 2건.\n\n" + FUNDING_DISCLAIMER) == ""


# --- 섹션 스트림 가드 ---


def test_모순된_판정_절은_폴백으로_교체된다():
    guard = ReportGuard(_RED, "### 판정\n\n**비추천** — 켜진 신호 1개")

    out = _run(guard, [("verdict", "### 판정\n\n**판정"), ("verdict", " 없음** 자료 부족"), ("reasons", "근거")])

    assert _joined(out)["verdict"] == "### 판정\n\n[확인된 사실] **비추천** — 켜진 신호 1개"


def test_판정_절은_절이_끝날_때_한_번에_나간다():
    guard = ReportGuard(_RED, "폴백")

    assert guard.feed([("verdict", "### 판정\n\n켜진 신호 "), ("verdict", "2개는 위험 신호다.")]) == []
    assert guard.feed([("reasons", "근거")])[0] == ("verdict", "### 판정\n\n[확인된 사실] 켜진 신호 2개는 위험 신호다.")


def test_다시_열린_판정_절이_모순이면_버린다():
    guard = ReportGuard(_RED, "폴백")

    out = _joined(
        _run(guard, [("verdict", "### 판정\n\n신호 2개."), ("reasons", "근거"), ("verdict", "\n\n경고 없음.")])
    )

    assert out["verdict"] == "### 판정\n\n[확인된 사실] 신호 2개."


def test_지원사업_절이_끝나면_고지문을_덧붙인다():
    out = _joined(_run(ReportGuard(None, ""), [("funding", "### 대안 업종 지원사업\n\n공고 2건.")]))

    assert out["funding"] == "### 대안 업종 지원사업\n\n[확인된 사실] 공고 2건.\n\n" + FUNDING_DISCLAIMER


def test_유사_사례_절은_태그를_붙이지_않는다():
    out = _joined(_run(ReportGuard(None, ""), [("analogs", "### 유사 사례\n코로나 때 약세.")]))

    assert out["analogs"] == "### 유사 사례\n코로나 때 약세."


def test_모든_절에서_링크를_지운다():
    out = _joined(_run(ReportGuard(None, ""), [("analogs", "### 유사 사례\n기사 https://n.kr/a 참고")]))

    assert out["analogs"] == "### 유사 사례\n기사 참고"


def test_한_절_통째로_가드를_씌운다():
    assert guard_section("reasons", "### 왜 안 되나\n\n분석 데이터가 부족합니다.") == (
        "### 왜 안 되나\n\n[확인된 사실] 분석 데이터가 부족합니다."
    )
    assert guard_section("funding", "### 대안 업종 지원사업\n\n분석 데이터가 부족합니다.").endswith(
        "\n\n" + FUNDING_DISCLAIMER
    )
