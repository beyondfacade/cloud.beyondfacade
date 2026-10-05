"""report_guards — 리포트 출력 코드 가드 순수 로직 (LLM·DB 없음)."""

from apps.agent.domain.services.report_guards import (
    FUNDING_DISCLAIMER,
    LeadingTagGuard,
    ReportGuard,
    UrlStripper,
    contradicts_verdict,
    disclaimer_suffix,
    guard_section,
    strip_links,
    verdict_contradiction,
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
    assert _stream(UrlStripper(), ["[원문](https://a.kr/x) 참고"]) == "참고"  # 이름표만 남는 링크는 통째로
    assert _stream(UrlStripper(), ["[https://a.kr](https://a.kr) 참고"]) == "참고"  # 줄 머리면 뒤 공백도 지운다


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


# --- 보강 (리뷰 1차): 실제 캐시 출력 모양 ---

_UNAVAILABLE = {"available": False, "reason": "표본 부족"}


def test_명시적_단정이_아닌_등급_말은_모순이_아니다():
    """리뷰가 실제로 짚은 오탐 다섯 — 등급 말이 나와도 등급을 단정한 게 아니다."""
    assert not contradicts_verdict("강한 위험 신호가 없고 약한 신호 1개만 켜져 있습니다.", _ORANGE)
    assert not contradicts_verdict("조건부로라도 진입을 권하기 어렵습니다.", _RED)
    assert not contradicts_verdict("경고 없이 넘길 상황이 아닙니다.", _RED)
    assert not contradicts_verdict("비추천 수준은 아닙니다.", _ORANGE)
    assert not contradicts_verdict("빨간불은 켜지지 않았습니다.", _CLEAR)


def test_다른_등급을_명시적으로_단정하면_모순이다():
    """캐시에 실제로 나온 단정 — 강조·등급 말·조사·괄호·줄 머리."""
    assert contradicts_verdict("판정\n판정 등급: **판정 없음**  \n신길제5동의 당구장", _RED)
    assert contradicts_verdict("판정\n판정 없음. 판정이 부여되지 않았습니다.", _CLEAR)
    assert contradicts_verdict("판정\n판정 등급은 red이며, 2개의 신호가 켜져 있습니다.", _ORANGE)
    assert contradicts_verdict("판정 등급은 **빨강(red)**으로 나타났습니다.", _CLEAR)
    assert contradicts_verdict("판정은 데이터 부족으로 인해 '판정 없음'이며", _RED)
    assert contradicts_verdict("현재 상황은 조건부입니다.", _RED)
    assert contradicts_verdict("비추천 등급입니다.", _UNAVAILABLE)
    assert contradicts_verdict("`clear`로 판정되었습니다.", _RED)


def test_같은_등급을_단정하면_모순이_아니다():
    assert not contradicts_verdict("판정 등급은 **판정 없음**입니다.", _UNAVAILABLE)
    assert not contradicts_verdict("**비추천** — 켜진 신호 1개", _RED)
    assert not contradicts_verdict("판정 보류 — 표본 부족", {"available": True, "verdict_code": "insufficient"})


def test_모르는_등급_코드는_대조하지_않는다():
    assert not contradicts_verdict("**비추천**", {"available": True, "verdict_code": "purple"})


def test_모순_이유는_단정한_구절이다():
    assert "판정 없음" in verdict_contradiction("판정 등급: **판정 없음**", _RED)
    assert verdict_contradiction("켜진 신호 2개", _RED) is None


# --- 제목 인식 ---


def _titled(title: str, pieces: list[str]) -> str:
    guard = LeadingTagGuard(title)
    return "".join(guard.feed(piece) for piece in pieces) + guard.flush()


def test_맨_제목_줄_다음_줄에_태그를_붙인다():
    assert _titled("왜 안 되나", ["왜 안 되나\n생존 절벽이 켜졌다."]) == "왜 안 되나\n[확인된 사실] 생존 절벽이 켜졌다."


def test_굵은_제목과_콜론_제목도_제목으로_본다():
    assert _titled("대안 업종 지원사업", ["**대안 업종 지원사업**\n공고 2건."]) == (
        "**대안 업종 지원사업**\n[확인된 사실] 공고 2건."
    )
    assert _titled("판정", ["판정**\n\n켜진 신호 2개."]) == "판정**\n\n[확인된 사실] 켜진 신호 2개."
    assert _titled("그래도 한다면", ["그래도 한다면:\n시간대"]) == "그래도 한다면:\n[확인된 사실] 시간대"


def test_제목_뒤_콜론에_이어_쓴_본문은_콜론_뒤에_태그를_붙인다():
    assert _titled("대안 동네·업종", ["대안 동네·업종: 같은 업종의 다른 동네는"]) == (
        "대안 동네·업종: [확인된 사실] 같은 업종의 다른 동네는"
    )


def test_제목으로_시작하는_문장은_제목이_아니다():
    assert _titled("판정", ["판정 없음 — 자료 부족"]) == "[확인된 사실] 판정 없음 — 자료 부족"


def test_제목이_조각으로_갈려도_인식한다():
    assert _titled("왜 안 되나", ["왜 안", " 되나", "\n", "생존"]) == "왜 안 되나\n[확인된 사실] 생존"


def test_제목이_아닌_본문은_줄_끝을_기다리지_않는다():
    guard = LeadingTagGuard("왜 안 되나")
    assert guard.feed("생존 절벽이 켜져 있어 오래 버티기 어려운 상권입니다") .startswith("[확인된 사실] 생존")


# --- 목록·표로 시작하는 본문 ---


def test_목록으로_시작하는_본문은_태그를_따로_한_문단으로_둔다():
    assert _titled("대안 동네·업종", ["대안 동네·업종\n- 제과점"]) == "대안 동네·업종\n[확인된 사실]\n\n- 제과점"
    assert _tagged(["### 대안\n\n1. 제과점"]) == "### 대안\n\n[확인된 사실]\n\n1. 제과점"
    assert _tagged(["* ", "제과점"]) == "[확인된 사실]\n\n* 제과점"
    assert _tagged(["| 업종 | 판정 |"]) == "[확인된 사실]\n\n| 업종 | 판정 |"
    assert _tagged(["> 인용"]) == "[확인된 사실]\n\n> 인용"


def test_숫자나_굵은_글씨로_시작하는_문장은_목록이_아니다():
    assert _tagged(["1,000만원 손실"]) == "[확인된 사실] 1,000만원 손실"
    assert _tagged(["**시간대 조건**: 저녁"]) == "[확인된 사실] **시간대 조건**: 저녁"


def test_굵은_태그도_이미_붙은_태그로_본다():
    assert _tagged(["**[확인된 사실]** 생존 절벽."]) == "**[확인된 사실]** 생존 절벽."
    assert _tagged(["**[참고", " 신호]** 뉴스."]) == "**[참고 신호]** 뉴스."


# --- 링크 흔적 정리 ---


def test_원문_링크_목록_항목은_줄째_지운다():
    url = "https://www.bizinfo.go.kr/sii/siia/selectSIIA200Detail.do?pblancId=PBLN_000000000123842"
    assert _stream(UrlStripper(), [f"*   [원문 링크]({url})\n*   다음"]) == "*   다음"
    assert _stream(UrlStripper(), [f"*   **원문 링크:** {url}\n다음"]) == "다음"
    assert _stream(UrlStripper(), [f"    - 링크: {url}\n다음"]) == "다음"
    assert _stream(UrlStripper(), [f"*   [원문 링크] {url}\n다음"]) == "다음"
    assert _stream(UrlStripper(), [f"*   **원문 링크**: {url}"]) == ""


def test_원문_링크_항목이_조각으로_갈려도_줄째_지운다():
    assert _stream(UrlStripper(), ["\n*", "   **원문", " 링크:** ", "https://a.kr/x", "\n다음"]) == "\n다음"


def test_링크_글자를_남긴_마크다운_링크와_괄호_흔적을_지운다():
    assert _stream(UrlStripper(), ["비용을 지원합니다. ([링크](https://a.kr/x))"]) == "비용을 지원합니다."
    assert _stream(UrlStripper(), ["[소상공인 정책자금](https://a.kr) 참고"]) == "소상공인 정책자금 참고"
    assert _stream(UrlStripper(), ["원문 `https://a.kr` 참고"]) == "원문 참고"
    assert _stream(UrlStripper(), ["공고 ([]()) 참고"]) == "공고 참고"
    assert _stream(UrlStripper(), ["공고(https/www…) 참고"]) == "공고 참고"
    assert _stream(UrlStripper(), ["공고 (**URL:** https://a.kr) 참고"]) == "공고 참고"
    assert _stream(UrlStripper(), ["공고 (링크: https://a.kr) 참고"]) == "공고 참고"


def test_조각으로_흘려도_통째와_같다():
    assert _stream(UrlStripper(), ["x ( h", "ttps://a.kr/x) y"]) == strip_links("x ( https://a.kr/x) y") == "x y"


def test_본문이_링크로_시작하면_앞_공백을_남기지_않는다():
    assert _stream(UrlStripper(), ["https://a.kr 본문"]) == "본문"
    assert _stream(UrlStripper(), ["앞 줄\n", "https://a.kr 뒤"]) == "앞 줄\n뒤"


def test_목록_항목은_링크가_없으면_그대로_나온다():
    assert _stream(UrlStripper(), ["- 제과", "점 (경고 없음)\n- 분식"]) == "- 제과점 (경고 없음)\n- 분식"


# --- 판정 절이 비면 폴백 / 개입 횟수 ---


def test_링크를_지워_판정_절이_비면_폴백을_낸다():
    guard = ReportGuard(_RED, "### 판정\n\n**비추천** — 켜진 신호 1개", titles={"verdict": "판정"})

    out = _joined(_run(guard, [("verdict", "판정\nhttps://a.kr/x")]))

    assert out["verdict"] == "### 판정\n\n[확인된 사실] **비추천** — 켜진 신호 1개"


def test_가드가_개입_횟수와_교체_이유를_남긴다():
    guard = ReportGuard(_RED, "### 판정\n\n**비추천**", titles={"verdict": "판정", "funding": "대안 업종 지원사업"})

    _run(guard, [
        ("verdict", "판정\n판정 등급: **판정 없음**"),
        ("reasons", "근거 https://a.kr 와 www.b.kr"),
        ("funding", "대안 업종 지원사업\n공고 PBLN_000000000123842"),
    ])

    assert dict(guard.events) == {"verdict_replaced": 1, "links_stripped": 3, "tags_added": 3, "disclaimer_added": 1}
    assert guard.replacements[0][0] == "verdict" and "판정 없음" in guard.replacements[0][1]


def test_캐시에서_놓친_단정도_잡는다():
    """'주의'는 강조나 등급 말과 함께일 때만, 괄호 속 코드, 문장 끝 등급 이름."""
    assert contradicts_verdict("판정\n전반적으로 '주의' 등급이 부여되었으며", _RED)
    assert contradicts_verdict("판정: 반포2동 카페 창업에 대해 ‘주의’(orange) 등급이 부여되었습니다.", _RED)
    assert contradicts_verdict("판정은 ‘주의 필요(orange)’ 단계입니다.", _RED)
    assert contradicts_verdict("**판정**: 노래방 상권은 충격에 직면해 판정 없음.", _CLEAR)
    assert not contradicts_verdict("주의: 이 수치는 표본이 작습니다. 주의가 필요합니다.", _RED)


def test_여는_괄호가_겹친_링크도_조각으로_흘리면_통째와_같다():
    """캐시 실측 모양 — `(\\``·`([링크](`·긴 링크 글자 `[…](` 앞부분이 링크보다 먼저 나가던 경우."""
    for text in (
        "금융 지원을 제공합니다 (`https://www.bizinfo.go.kr/a?pblancId=PBLN_1`).\n- 다음",
        "금융 지원을 제공합니다. ([링크](https://www.bizinfo.go.kr/a))\n- 다음",
        "   - **링크**: [서울특별시 위기 소상공인 지원 사업 모집 공고](https://www.bizinfo.go.kr/a)\n다음",
    ):
        pieces = [text[i : i + 3] for i in range(0, len(text), 3)]
        assert _stream(UrlStripper(), pieces) == strip_links(text), text


def test_긴_원문_링크_항목도_줄바꿈까지_함께_지운다():
    text = "지원합니다.\n    *   [원문 링크](https://www.bizinfo.go.kr/sii/siia/selectSIIA200Detail.do?pblancId=PBLN_1)\n*   다음"
    pieces = [text[i : i + 3] for i in range(0, len(text), 3)]
    assert _stream(UrlStripper(), pieces) == strip_links(text) == "지원합니다.\n*   다음"


def test_괄호_속_이름표가_조각으로_갈려도_통째와_같다():
    """캐시 실측 — `    (원문 링크: https://…)` 줄. `(원문`이 먼저 나가면 `(원문)`이 남았다."""
    text = (
        "까지입니다.\n    (원문 링크: https://www.bizinfo.go.kr/a.do?pblancId=PBLN_1)\n"
        "*   **2026년 하반기**: 지원합니다. 공고 **원문 링크:** https://a.kr 참고"
    )
    for size in (1, 3, 7):
        pieces = [text[i : i + size] for i in range(0, len(text), size)]
        assert _stream(UrlStripper(), pieces) == strip_links(text), size


# --- 마무리 (리뷰 2차) ---


def test_소제목이나_코드_블록으로_시작하는_본문은_태그를_따로_한_문단으로_둔다():
    """캐시 실측(exaone s04·s02) — `#### 대안 동네`가 `[확인된 사실] #### 대안 동네`로 깨졌다."""
    assert _titled("대안 동네·업종", ["대안 동네·업종\n#### 대안 동네\n- **부암동**"]) == (
        "대안 동네·업종\n[확인된 사실]\n\n#### 대안 동네\n- **부암동**"
    )
    assert _titled("대안 업종 지원사업", ["대안 업종 지원사업\n#", "### 한식 업종 관련 지원사업"]) == (
        "대안 업종 지원사업\n[확인된 사실]\n\n#### 한식 업종 관련 지원사업"
    )
    assert _tagged(["``", "`\ncode\n```"]) == "[확인된 사실]\n\n```\ncode\n```"


def test_등급_말_뒤의_부정은_단정이_아니다():
    assert not contradicts_verdict("비추천 등급은 아니지만 신호 1개가 켜져 있습니다.", _ORANGE)
    assert not contradicts_verdict("조건부 판정은 아닙니다.", _CLEAR)
    assert not contradicts_verdict("**비추천** 등급은 아니며 주의가 필요합니다.", _ORANGE)
    assert contradicts_verdict("비추천 등급은 아니지만 판정 등급은 **조건부**입니다.", _RED)  # 뒤의 단정은 잡는다


def test_긴_공백도_선형_시간에_처리한다():
    import time

    text = "앞" + " " * 20000 + "뒤 https://a.kr 끝"
    started = time.perf_counter()
    whole = strip_links(text)
    streamed = _stream(UrlStripper(), [text[i : i + 5] for i in range(0, len(text), 5)])
    guarded = guard_section("reasons", text, "왜 안 되나")
    assert time.perf_counter() - started < 0.5
    assert whole == streamed and guarded.endswith("뒤 끝")
