"""같은 사건 기사 접기 — 순수 함수. 제목 토큰 유사도 + 보도일 창으로 판정, 점수 높은 기사만 남긴다."""

from datetime import datetime

from apps.rag.domain.entities.rag_chunk_entity import RagHit
from apps.rag.domain.services.same_event_collapser import collapse_same_event, same_event


def _hit(cid: str, title: str, score: float, day: int = 21, desc: str = "본문 요약") -> RagHit:
    return RagHit(chunk_id=cid, source_type="news", source_id=cid, content=f"{title}\n{desc}",
                  score=score, url=None, org=None, published_at=datetime(2026, 9, day))


def test_같은_보도자료_기사들은_점수_높은_하나만_남는다():
    hits = [
        _hit("a", "코웨이, 롯데백화점 노원점에 올해 10번째 직영매장 개점", 0.9),
        _hit("b", "코웨이, 롯데百 노원점에 10번째 공식 직영매장…서울 동북권", 0.88),
        _hit("c", "코웨이, 노원 롯데백화점에 올해 10번째 직영매장", 0.85),
    ]
    assert [h.chunk_id for h in collapse_same_event(hits)] == ["a"]


def test_다른_사건은_남고_순서는_점수순_그대로다():
    hits = [
        _hit("a", "코웨이, 롯데백화점 노원점에 올해 10번째 직영매장 개점", 0.9),
        _hit("b", "홈앤쇼핑, 둔촌역전통시장서 디지털 전환 지원", 0.8, day=25),
        _hit("c", "코웨이, 노원 롯데백화점에 올해 10번째 직영매장", 0.7),
        _hit("d", "종로구, 8년 연속 행정서비스 1위", 0.6, day=10),
    ]
    assert [h.chunk_id for h in collapse_same_event(hits)] == ["a", "b", "d"]


def test_제목이_비슷해도_보도일이_멀면_다른_사건이다():
    a = _hit("a", "[위클리오늘] 부산 중구 소식", 0.9, day=15)
    b = _hit("b", "[위클리오늘] 부산 중구 소식", 0.8, day=28)
    assert not same_event(a, b)
    assert [h.chunk_id for h in collapse_same_event([a, b])] == ["a", "b"]


def test_보도일이_없으면_제목만으로_판정한다():
    a = _hit("a", "신중앙시장 187억 디자인혁신 착공", 0.9)
    b = RagHit(chunk_id="b", source_type="news", source_id="b", content="신중앙시장 187억 디자인혁신 첫 삽\n요약",
               score=0.8, url=None, org=None, published_at=None)
    assert same_event(a, b)


def test_빈_입력과_단건은_그대로다():
    assert collapse_same_event([]) == []
    one = [_hit("a", "제목", 0.5)]
    assert collapse_same_event(one) == one
