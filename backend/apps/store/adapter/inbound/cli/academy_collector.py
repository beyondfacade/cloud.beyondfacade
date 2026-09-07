"""학원·교습소 수집기 (Driving Adapter, CLI).

- 원천: 서울 열린데이터광장 OA-20528 (neisAcademyInfo) — 현행 스냅샷 전량, 매 실행 멱등 재수집
- 적재: store 업서트(industry_id=academy) + academy_course 재적재(delete+insert)
- 실행: python -m apps.store.adapter.inbound.cli.academy_collector
"""

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.store.adapter.outbound.gateways.seoul_academy_gateway import SeoulAcademyGateway
from apps.store.adapter.outbound.repositories.academy_course_repository import (
    SqlAlchemyAcademyCourseRepository,
)
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.use_cases.academy_course_interactor import AcademyCourseInteractor
from core.matrix.grid_oracle_database_manager import session_scope


def main() -> None:
    with session_scope() as session:
        district_codes = dict(
            session.execute(select(DistrictOrm.name, DistrictOrm.district_code)).all()
        )

    gateway = SeoulAcademyGateway(district_codes=district_codes)
    interactor = AcademyCourseInteractor(
        store_repository=SqlAlchemyStoreRepository(),
        course_repository=SqlAlchemyAcademyCourseRepository(),
        gateway=gateway,
    )
    stores, courses = interactor.ingest()
    print(
        f"academy collector: 점포 {stores}건 업서트, 교습과정 {courses}건 재적재"
        f" (API {gateway.call_count}회 호출)",
        flush=True,
    )
    if gateway.skipped_districts:
        print(f"academy collector: 구 미매칭 스킵 {gateway.skipped_districts}", flush=True)


if __name__ == "__main__":
    main()
