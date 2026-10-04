"""hit_at_k·mrr 순수 함수 — 적중/미적중/다중정답/역순/top-k 밖. DB·네트워크 없음.

relevant는 동치 집합(뉴스 같은 사건 기사 여럿) — 하나라도 top-k에 있으면 Hit 1.0, MRR은 첫 적중 순위.
"""

from apps.rag.adapter.inbound.cli.evaluate_rag import hit_at_k, mrr


def test_적중_관련문서가_상위_k안에_있으면_hit과_mrr_모두_1점():
    assert hit_at_k({"funding:A"}, ["funding:A", "funding:B", "funding:C"], k=5) == 1.0
    assert mrr({"funding:A"}, ["funding:A", "funding:B", "funding:C"]) == 1.0


def test_미적중_관련문서가_랭킹에_없으면_hit과_mrr_모두_0점():
    assert hit_at_k({"funding:Z"}, ["funding:A", "funding:B", "funding:C"], k=5) == 0.0
    assert mrr({"funding:Z"}, ["funding:A", "funding:B", "funding:C"]) == 0.0


def test_다중정답_동치집합_중_하나만_상위_k안에_있어도_hit은_1점_mrr은_첫적중순위():
    assert hit_at_k({"news:A", "news:Z"}, ["news:B", "news:A", "news:C"], k=5) == 1.0
    assert mrr({"news:A", "news:Z"}, ["news:B", "news:A", "news:C"]) == 1 / 2


def test_역순_관련문서가_랭킹_맨끝에_있으면_hit은_1점이지만_mrr은_낮은_점수():
    ranked = ["funding:A", "funding:B", "funding:C", "funding:D", "funding:E"]
    assert hit_at_k({"funding:E"}, ranked, k=5) == 1.0
    assert mrr({"funding:E"}, ranked) == 1 / 5


def test_top_k_밖의_적중은_hit에_안_잡힌다():
    ranked = ["funding:A", "funding:B", "funding:C", "funding:D", "funding:E", "funding:F"]
    assert hit_at_k({"funding:F"}, ranked, k=5) == 0.0
    assert mrr({"funding:F"}, ranked) == 1 / 6
