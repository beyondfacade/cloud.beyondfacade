"""analysis 라우터 — POST /analysis + SSE 이벤트 + myself 배선 검증."""

import json
import time
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from apps.agent.adapter.inbound.api.schemas.analysis_schema import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisMyselfResponse,
)
from apps.agent.adapter.outbound.repositories.analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from apps.agent.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.agent.dependencies.analysis_dependencies import (
    build_analysis_use_case,
    get_analysis_repository,
    get_analysis_use_case,
)
from apps.agent.domain.entities.agent_event_entity import AgentEvent

router = APIRouter(prefix="/analysis", tags=["analysis"])

# 프로세스 수명 pending — mock 대칭 (analysis_id → 요청 파라미터)
_PENDING: dict[str, dict] = {}


@router.get("/myself", response_model=AnalysisMyselfResponse)
def myself(
    use_case: AnalysisUseCase = Depends(get_analysis_use_case),
) -> AnalysisMyselfResponse:
    return AnalysisMyselfResponse(**use_case.myself())


@router.post("", response_model=AnalysisCreateResponse)
def create_analysis(body: AnalysisCreateRequest) -> AnalysisCreateResponse:
    analysis_id = uuid.uuid4().hex
    _PENDING[analysis_id] = {
        "region": body.region,
        "industry": body.industry,
        "question": body.question,
        "model": body.model,
    }
    return AnalysisCreateResponse(analysis_id=analysis_id)


@router.get("/{analysis_id}/events", response_model=None)
def stream_events(
    analysis_id: str,
    request: Request,
    repository: SqlAlchemyAnalysisRepository = Depends(get_analysis_repository),
) -> StreamingResponse | JSONResponse:
    pending = _PENDING.get(analysis_id)
    if pending is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "ANALYSIS_NOT_FOUND",
                    "message": f"분석을 찾을 수 없습니다: {analysis_id}",
                }
            },
        )

    def event_stream() -> Iterator[bytes]:
        override = request.app.dependency_overrides.get(get_analysis_use_case)
        use_case = override() if override is not None else build_analysis_use_case(
            pending["model"]
        )
        sections: list[str] = []
        citations: list[dict] = []
        started = time.monotonic()
        try:
            for event in use_case.run(
                pending["region"], pending["industry"], pending["question"]
            ):
                frame_event = _with_stable_report_id(event, analysis_id)
                if frame_event.type == "report_delta":
                    sections.append(frame_event.payload.get("markdown") or "")
                elif frame_event.type == "report_done":
                    citations = list(frame_event.payload.get("citations") or [])
                yield _sse_frame(frame_event).encode("utf-8")
        finally:
            # Fake/override 경로에서는 DB 영속화를 건너뛴다 (라우터 단위 테스트)
            if override is None:
                latency_ms = int((time.monotonic() - started) * 1000)
                usage = getattr(use_case, "last_usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
                model_name = pending["model"]
                llm = getattr(use_case, "_llm", None)
                if llm is not None and getattr(llm, "model_name", None):
                    model_name = llm.model_name
                try:
                    repository.save_report(
                        analysis_id=analysis_id,
                        region_code=pending["region"],
                        industry=pending["industry"],
                        question=pending["question"],
                        report_md="\n\n".join(sections),
                        citations=citations,
                        model=model_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        latency_ms=latency_ms,
                    )
                except Exception:
                    # 영속화 실패로 SSE 클라이언트를 끊지 않는다 — 스트림은 이미 전송됨
                    pass
            _PENDING.pop(analysis_id, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _with_stable_report_id(event: AgentEvent, analysis_id: str) -> AgentEvent:
    """영속 PK = analysis_id 계약 — report_done.report_id를 정렬한다."""
    if event.type != "report_done":
        return event
    payload = {**event.payload, "report_id": analysis_id}
    return AgentEvent(type=event.type, payload=payload)


def _sse_frame(event: AgentEvent) -> str:
    data = json.dumps({"type": event.type, **event.payload}, ensure_ascii=False)
    return f"event: {event.type}\ndata: {data}\n\n"
