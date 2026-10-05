"""report_guards — 리포트 출력 코드 가드 순수 로직 (LLM·DB 없음)."""

from apps.agent.domain.services.report_guards import (
    UrlStripper,
    contradicts_verdict,
    drop_digit_sentences,
    guard_answer,
    strip_links,
    verdict_contradiction,
)

_RED = {"available": True, "verdict_code": "red"}
_ORANGE = {"available": True, "verdict_code": "orange"}
_CLEAR = {"available": True, "verdict_code": "clear"}


def _stream(stripper: UrlStripper, pieces: list[str]) -> str:
    return "".join(stripper.feed(piece) for piece in pieces) + stripper.flush()


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
    assert time.perf_counter() - started < 0.5
    assert whole == streamed and whole.endswith("뒤 끝")


# --- 해석(answer) 단락 숫자 가드 (2026-10-05 코드 우선 구조) ---


def test_숫자가_든_문장만_지우고_지운_수를_센다():
    assert drop_digit_sentences("폐업이 많습니다. 폐업률은 31%입니다. 대안을 보세요.") == ("폐업이 많습니다. 대안을 보세요.", 1)


def test_판정과_모순된_해석은_통과하지_못한다():
    got = guard_answer("판정은 **경고 없음**입니다. 해 볼 만합니다.", _RED)

    assert got.ok is False and got.contradiction == "판정은 **경고 없음"


def test_숫자_문장만_있던_해석은_가드_뒤_비어_통과하지_못한다():
    got = guard_answer("매출은 1,200만원입니다. 폐업률은 31%입니다.", _RED)

    assert (got.text, got.removed_sentences, got.ok) == ("", 2, False)
