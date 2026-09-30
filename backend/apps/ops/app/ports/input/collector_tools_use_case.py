"""Driving Port — 수집기 로그 보기·수동 실행 (운영 관리자)."""

from abc import ABC, abstractmethod

from apps.ops.app.dtos.ops_history_dto import CollectorLogDto, CollectorRunDto, OpsActorDto


class CollectorToolsUseCase(ABC):
    @abstractmethod
    def myself(self) -> CollectorLogDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def log(self, key: str, lines: int) -> CollectorLogDto:
        """카탈로그에 없는 key는 UnknownCollector. 비밀값은 가려서 돌려준다."""

    @abstractmethod
    def run(self, key: str, actor: OpsActorDto) -> CollectorRunDto:
        """이미 돌고 있으면 CollectorRunning. 실행은 감사 로그에 남는다."""
