"""recall_at_k·mrr 순수 함수 — 4케이스(적중/미적중/부분/역순). DB·네트워크 없음."""

from apps.rag.adapter.inbound.cli.evaluate_rag import mrr, recall_at_k


def test_적중_관련문서가_상위_k안에_있으면_recall과_mrr_모두_1점():
    relevant = {"funding:A"}
    ranked = ["funding:A", "funding:B", "funding:C"]

    assert recall_at_k(relevant, ranked, k=5) == 1.0
    assert mrr(relevant, ranked) == 1.0


def test_미적중_관련문서가_랭킹에_없으면_recall과_mrr_모두_0점():
    relevant = {"funding:Z"}
    ranked = ["funding:A", "funding:B", "funding:C"]

    assert recall_at_k(relevant, ranked, k=5) == 0.0
    assert mrr(relevant, ranked) == 0.0


def test_부분적중_관련문서_2건중_1건만_상위_k안에_있으면_recall은_절반_mrr은_첫적중순위():
    relevant = {"funding:A", "funding:Z"}
    ranked = ["funding:B", "funding:A", "funding:C"]

    assert recall_at_k(relevant, ranked, k=5) == 0.5
    assert mrr(relevant, ranked) == 1 / 2


def test_역순_관련문서가_랭킹_맨끝에_있으면_recall은_1점이지만_mrr은_낮은_점수():
    relevant = {"funding:E"}
    ranked = ["funding:A", "funding:B", "funding:C", "funding:D", "funding:E"]

    assert recall_at_k(relevant, ranked, k=5) == 1.0
    assert mrr(relevant, ranked) == 1 / 5
