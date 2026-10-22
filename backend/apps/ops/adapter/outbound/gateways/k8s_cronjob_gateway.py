"""EKS 수집기 — CronJob 상태·Job 파드 로그·수동 Job을 클러스터 API로 본다 (파드엔 logs/·scripts/가 없다)."""

import os
import ssl
from datetime import datetime
from pathlib import Path

import httpx

from apps.ops.app.ports.output.facility_port import CollectorLogPort, CollectorRunnerPort

_SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")
_TIMEOUT = 5.0


def in_cluster() -> bool:
    return "KUBERNETES_SERVICE_HOST" in os.environ


class K8sCronJobGateway(CollectorLogPort, CollectorRunnerPort):
    """카탈로그 key = CronJob 이름, 로그 파일명 = `<key>.log`."""

    def __init__(self, client: httpx.Client | None = None, namespace: str | None = None) -> None:
        self._client = client
        self._namespace = namespace
        self._cronjobs: dict[str, dict] | None = None  # 요청마다 새 인스턴스 — 한 화면 조회 동안만 재사용

    def last_modified(self, log_file: str) -> datetime | None:
        succeeded = self._cronjob(_key(log_file)).get("status", {}).get("lastSuccessfulTime")
        return _parse_time(succeeded) if succeeded else None

    def tail(self, log_file: str, lines: int) -> list[str]:
        try:
            jobs = self._jobs(_key(log_file))
            if not jobs:
                return []
            latest = max(jobs, key=lambda job: job["metadata"]["creationTimestamp"])
            pods = self._get("pods", params={"labelSelector": f"job-name={latest['metadata']['name']}"})["items"]
            if not pods:
                return []
            pod = max(pods, key=lambda p: p["metadata"]["creationTimestamp"])["metadata"]["name"]
            text = self._request("GET", f"/api/v1/namespaces/{self._ns()}/pods/{pod}/log", params={"tailLines": lines}).text
        except httpx.HTTPError:
            return []
        return text.splitlines()

    def is_running(self, key: str) -> bool:
        try:
            return any(job.get("status", {}).get("active") for job in self._jobs(key))
        except httpx.HTTPError:
            return False

    def start(self, key: str) -> None:
        cronjob = self._cronjob(key)
        if not cronjob:
            raise RuntimeError(f"CronJob이 없습니다: {key}")
        template = cronjob["spec"]["jobTemplate"]
        job = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "generateName": f"{key}-manual-",
                "labels": template.get("metadata", {}).get("labels", {}),
                "annotations": {"cronjob.kubernetes.io/instantiate": "manual"},
                "ownerReferences": [
                    {
                        "apiVersion": "batch/v1",
                        "kind": "CronJob",
                        "name": key,
                        "uid": cronjob["metadata"]["uid"],
                        "controller": True,
                    }
                ],
            },
            "spec": template["spec"],
        }
        self._request("POST", f"/apis/batch/v1/namespaces/{self._ns()}/jobs", json=job)

    def _cronjob(self, key: str) -> dict:
        if self._cronjobs is None:
            try:
                items = self._get("cronjobs")["items"]
            except httpx.HTTPError:
                items = []
            self._cronjobs = {item["metadata"]["name"]: item for item in items}
        return self._cronjobs.get(key, {})

    def _jobs(self, key: str) -> list[dict]:
        return [
            job
            for job in self._get("jobs")["items"]
            if any(o.get("kind") == "CronJob" and o.get("name") == key for o in job["metadata"].get("ownerReferences", []))
        ]

    def _get(self, resource: str, params: dict | None = None) -> dict:
        group = "/api/v1" if resource.startswith("pods") else "/apis/batch/v1"
        return self._request("GET", f"{group}/namespaces/{self._ns()}/{resource}", params=params).json()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._client is not None:
            response = self._client.request(method, path, **kwargs)
        else:
            base = f"https://{os.environ['KUBERNETES_SERVICE_HOST']}:{os.environ['KUBERNETES_SERVICE_PORT']}"
            token = (_SA_DIR / "token").read_text()  # 토큰은 주기적으로 갈린다 — 매번 읽는다
            with httpx.Client(
                base_url=base, verify=ssl.create_default_context(cafile=_SA_DIR / "ca.crt"), timeout=_TIMEOUT,
                headers={"Authorization": f"Bearer {token}"},
            ) as client:
                response = client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    def _ns(self) -> str:
        if self._namespace is None:
            self._namespace = (_SA_DIR / "namespace").read_text().strip()
        return self._namespace


def _key(log_file: str) -> str:
    return Path(log_file).name.removesuffix(".log")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
