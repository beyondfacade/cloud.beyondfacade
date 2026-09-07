"""시드 파일 Driven Adapter — 문서화된 정책 충격 시드(출처 필수)를 엔티티로 읽는다.

seed/shock_events_seed.json: ①계층(정책·규제) 충격 중 API 미커버 구간
(1차 거리두기 2020-03-22~2020-12-07, 위드코로나 이후 재강화)과 공표 시행일이 명확한
정책 충격(최저임금 고시, 주 52시간제, 재난지원금·손실보상)을 담는다 — brainstorming §5.2.
"""

import json
from datetime import date
from pathlib import Path

from apps.shock.app.ports.output.shock_event_port import ShockEventSourcePort
from apps.shock.domain.entities.shock_event_entity import IndustryImpact, ShockEvent

_SEED_PATH = Path(__file__).resolve().parent / "seed" / "shock_events_seed.json"


def _to_event(row: dict) -> ShockEvent:
    end_date = row.get("end_date")
    return ShockEvent(
        event_id=row["event_id"],
        layer=row["layer"],
        name=row["name"],
        start_date=date.fromisoformat(row["start_date"]),
        end_date=date.fromisoformat(end_date) if end_date else None,
        scope=row["scope"],
        source=row["source"],  # 필수 — 엔티티 불변식이 공출처 없는 행을 거부한다
        source_url=row.get("source_url"),
        description=row.get("description"),
        industry_impacts=[
            IndustryImpact(impact["industry_id"], impact["severity"])
            for impact in row.get("industry_impacts", [])
        ],
    )


class ShockSeedGateway(ShockEventSourcePort):
    def __init__(self, seed_path: Path = _SEED_PATH) -> None:
        self._seed_path = seed_path

    def fetch_events(self) -> list[ShockEvent]:
        with open(self._seed_path, encoding="utf-8") as f:
            return [_to_event(row) for row in json.load(f)["events"]]
