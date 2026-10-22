import json
from datetime import UTC, datetime

import httpx

from apps.ops.adapter.outbound.gateways.k8s_cronjob_gateway import K8sCronJobGateway

_OWNER = [{"kind": "CronJob", "name": "news-poller"}]


def _gateway(created: list[dict]) -> K8sCronJobGateway:
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST":
            created.append(json.loads(request.content))
            return httpx.Response(201, json={})
        if path.endswith("/cronjobs"):
            return httpx.Response(200, json={"items": [
                {
                    "metadata": {"name": "news-poller", "uid": "u1"},
                    "status": {"lastSuccessfulTime": "2026-10-22T03:10:09Z"},
                    "spec": {"jobTemplate": {"spec": {"backoffLimit": 0}}},
                },
            ]})
        if path.endswith("/jobs"):
            return httpx.Response(200, json={"items": [
                {"metadata": {"name": "news-poller-1", "creationTimestamp": "2026-10-22T02:10:00Z", "ownerReferences": _OWNER}, "status": {}},
                {"metadata": {"name": "news-poller-2", "creationTimestamp": "2026-10-22T03:10:00Z", "ownerReferences": _OWNER}, "status": {"active": 1}},
                {"metadata": {"name": "other-1", "creationTimestamp": "2026-10-22T04:00:00Z"}, "status": {"active": 1}},
            ]})
        if path.endswith("/pods"):
            assert request.url.params["labelSelector"] == "job-name=news-poller-2"
            return httpx.Response(200, json={"items": [{"metadata": {"name": "p2", "creationTimestamp": "2026-10-22T03:10:01Z"}}]})
        if path.endswith("/pods/p2/log"):
            return httpx.Response(200, text="a\nb\n")
        return httpx.Response(404)

    return K8sCronJobGateway(client=httpx.Client(transport=httpx.MockTransport(handle), base_url="http://k8s"), namespace="ns")


def test_CronJob_성공_시각_최근_Job_로그_실행_중을_읽는다():
    gateway = _gateway([])
    assert gateway.last_modified("news-poller.log") == datetime(2026, 10, 22, 3, 10, 9, tzinfo=UTC)
    assert gateway.last_modified("none.log") is None
    assert gateway.tail("news-poller.log", 10) == ["a", "b"]
    assert gateway.is_running("news-poller") is True
    assert gateway.is_running("none") is False


def test_수동_실행은_CronJob_템플릿으로_Job을_만든다():
    created: list[dict] = []
    _gateway(created).start("news-poller")
    job = created[0]
    assert job["metadata"]["generateName"] == "news-poller-manual-"
    assert job["metadata"]["ownerReferences"][0]["uid"] == "u1"
    assert job["spec"] == {"backoffLimit": 0}
