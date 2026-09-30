"""운영자가 지금 진행 중인 이벤트를 유형과 함께 등록한다 (Driving Adapter, CLI).

유형이 붙은 진행 중 이벤트는 리포트의 '유사 사례' 절이 기본으로 참고한다 — 같은 유형의
지난 이벤트를 찾아 그때 업종별로 무슨 일이 있었는지 비교한다. 같은 event_id로 다시 실행하면 갱신한다.

실행 예:
  python -m apps.shock.adapter.inbound.cli.register_shock_event \\
    --event-id outbreak-xvirus-20260901 --category pandemic \\
    --name "신종 호흡기 바이러스 국내 유행" --start 2026-09-01 \\
    --source "질병관리청 보도자료" [--end 2026-12-31] [--scope 전국] [--description ...]
"""

import argparse
from datetime import date

from apps.shock.adapter.outbound.repositories.shock_event_repository import (
    SqlAlchemyShockEventRepository,
)
from apps.shock.app.use_cases.shock_event_interactor import ShockEventInteractor
from apps.shock.domain.entities.shock_event_entity import ShockEvent
from apps.shock.domain.value_objects.event_category import EventCategory
from apps.shock.domain.value_objects.shock_layer import ShockLayer


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="진행 중 이벤트 등록")
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--category", required=True, choices=[c.value for c in EventCategory])
    parser.add_argument("--name", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--source", required=True, help="근거 출처 (기관·고시·보도자료)")
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--layer", default=ShockLayer.POLICY.value, choices=[l.value for l in ShockLayer])
    parser.add_argument("--scope", default="전국")
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--description", default=None)
    return parser


def main() -> None:
    args = _parser().parse_args()
    event = ShockEvent(
        event_id=args.event_id,
        layer=args.layer,
        name=args.name,
        start_date=args.start,
        end_date=args.end,
        scope=args.scope,
        source=args.source,
        source_url=args.source_url,
        description=args.description,
        category=args.category,
    )
    inserted, updated = ShockEventInteractor(repository=SqlAlchemyShockEventRepository()).register(event)
    print(f"shock event: 신규 {inserted}건 / 갱신 {updated}건 — {event.event_id} ({event.category})")


if __name__ == "__main__":
    main()
