from itertools import batched

from apps.store.app.ports.input.academy_course_use_case import AcademyIngestUseCase
from apps.store.app.ports.output.academy_course_port import (
    AcademyCourseRepositoryPort,
    AcademyGatewayPort,
)
from apps.store.app.ports.output.store_port import StoreRepositoryPort

_CHUNK_SIZE = 500


class AcademyCourseInteractor(AcademyIngestUseCase):
    def __init__(
        self,
        store_repository: StoreRepositoryPort,
        course_repository: AcademyCourseRepositoryPort,
        gateway: AcademyGatewayPort,
    ) -> None:
        self._store_repository = store_repository
        self._course_repository = course_repository
        self._gateway = gateway

    def ingest(self) -> tuple[int, int]:
        stores = 0
        courses = 0
        for chunk in batched(self._gateway.iter_academies(), _CHUNK_SIZE):
            # store를 먼저 커밋해야 course의 FK(store_id)가 성립한다
            stores += self._store_repository.upsert([record.store for record in chunk])
            courses += self._course_repository.replace_for_stores(
                {record.store.store_id: record.courses for record in chunk}
            )
        return stores, courses
