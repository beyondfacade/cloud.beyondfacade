"""아파트 매매 건수 적재 러너 (Driving Adapter, CLI) — 업종 특화 신호 설계서 §11.

- 25개 구 × 월(--from ~ --to, 기본 --to = 지난달). 이미 적재된 (구, 월)은 건너뛴다(--refresh로 다시).
- 멱등: PK (district_code, legal_dong, deal_ym) INSERT … ON CONFLICT DO UPDATE.
- 일일 호출 한도에 걸리면 MolitApiError로 멈춘다 — 다음 날 같은 명령을 다시 실행하면 이어서 받는다.

실행: python -m apps.housing.adapter.inbound.cli.load_apt_trade_counts --from 202101
"""

import argparse
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from apps.housing.adapter.outbound.gateways.molit_apt_trade_gateway import MolitAptTradeGateway
from apps.housing.adapter.outbound.orms.apt_trade_count_orm import AptTradeCountOrm
from apps.housing.domain.entities.apt_trade_count_entity import AptTradeCount
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from core.matrix.grid_oracle_database_manager import session_scope


def month_range(start: str, end: str) -> list[str]:
    first = int(start[:4]) * 12 + int(start[4:]) - 1
    last = int(end[:4]) * 12 + int(end[4:]) - 1
    return [f"{m // 12}{m % 12 + 1:02d}" for m in range(first, last + 1)]


def upsert_counts(rows: list[AptTradeCount], collected_at: datetime) -> int:
    if not rows:
        return 0
    statement = insert(AptTradeCountOrm).values([
        {"district_code": r.district_code, "legal_dong": r.legal_dong, "deal_ym": r.deal_ym,
         "trade_count": r.trade_count, "collected_at": collected_at}
        for r in rows
    ])
    with session_scope() as session:
        session.execute(statement.on_conflict_do_update(
            index_elements=["district_code", "legal_dong", "deal_ym"],
            set_={"trade_count": statement.excluded.trade_count, "collected_at": statement.excluded.collected_at},
        ))
    return len(rows)


def _last_month(today: date) -> str:
    return f"{today.year - 1}12" if today.month == 1 else f"{today.year}{today.month - 1:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="아파트 매매 건수 적재 (설계서 §11)")
    parser.add_argument("--from", dest="start", default="202101")
    parser.add_argument("--to", dest="end", default=_last_month(date.today()))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    gateway = MolitAptTradeGateway()
    with session_scope() as session:
        districts = session.execute(select(DistrictOrm.district_code).order_by(DistrictOrm.district_code)).scalars().all()
        done = set(session.execute(select(AptTradeCountOrm.district_code, AptTradeCountOrm.deal_ym).distinct()).all())
    total = 0
    for deal_ym in month_range(args.start, args.end):
        for district in districts:
            if not args.refresh and (district, deal_ym) in done:
                continue
            counts = gateway.month_counts(district, deal_ym)
            total += upsert_counts(
                [AptTradeCount(district, dong, deal_ym, n) for dong, n in counts.items()], datetime.now(timezone.utc)
            )
        print(f"{deal_ym} 적재 누적 {total}행")


if __name__ == "__main__":
    main()
