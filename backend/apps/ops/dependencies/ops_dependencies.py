"""Composition Root (DIP) — ops BC Port에 Adapter를 주입한다."""

from apps.ops.adapter.outbound.gateways.admin_audit_gateway import AdminAuditGateway
from apps.ops.adapter.outbound.gateways.collector_log_gateway import CollectorLogGateway
from apps.ops.adapter.outbound.gateways.llm_call_gateway import LlmCallGateway
from apps.ops.adapter.outbound.gateways.llm_chain_gateway import LlmChainGateway
from apps.ops.adapter.outbound.gateways.llm_usage_gateway import LlmUsageGateway
from apps.ops.adapter.outbound.gateways.nvidia_smi_gateway import NvidiaSmiGateway
from apps.ops.adapter.outbound.gateways.ollama_status_gateway import OllamaStatusGateway
from apps.ops.adapter.outbound.gateways.postgres_status_gateway import PostgresStatusGateway
from apps.ops.adapter.outbound.gateways.probe_gateways import LlmProbe, RagProbe
from apps.ops.adapter.outbound.gateways.proc_host_gateway import ProcHostGateway
from apps.ops.adapter.outbound.gateways.rag_stats_gateway import RagStatsGateway
from apps.ops.adapter.outbound.gateways.script_runner_gateway import ScriptRunnerGateway
from apps.ops.adapter.outbound.repositories.host_sample_repository import SqlAlchemyHostSampleRepository
from apps.ops.app.ports.input.collector_tools_use_case import CollectorToolsUseCase
from apps.ops.app.ports.input.facility_use_case import FacilityUseCase
from apps.ops.app.ports.input.healthcare_use_case import HealthcareUseCase
from apps.ops.app.ports.input.host_history_use_case import HostHistoryUseCase
from apps.ops.app.use_cases.collector_tools_interactor import CollectorToolsInteractor
from apps.ops.app.use_cases.facility_interactor import FacilityInteractor
from apps.ops.app.use_cases.healthcare_interactor import HealthcareInteractor
from apps.ops.app.use_cases.host_history_interactor import HostHistoryInteractor


def get_healthcare_use_case() -> HealthcareUseCase:
    return HealthcareInteractor(
        ollama=OllamaStatusGateway(),
        chain=LlmChainGateway(),
        usage=LlmUsageGateway(),
        rag=RagStatsGateway(),
        probes={"rag": RagProbe(), "llm": LlmProbe()},
        calls=LlmCallGateway(),
        audit=AdminAuditGateway(),
    )


def get_facility_use_case() -> FacilityUseCase:
    return FacilityInteractor(
        host=ProcHostGateway(),
        gpus=NvidiaSmiGateway(),
        database=PostgresStatusGateway(),
        ollama=OllamaStatusGateway(),
        logs=CollectorLogGateway(),
    )


def get_host_history_use_case() -> HostHistoryUseCase:
    return HostHistoryInteractor(
        host=ProcHostGateway(), gpus=NvidiaSmiGateway(), samples=SqlAlchemyHostSampleRepository()
    )


def get_collector_tools_use_case() -> CollectorToolsUseCase:
    return CollectorToolsInteractor(logs=CollectorLogGateway(), runner=ScriptRunnerGateway(), audit=AdminAuditGateway())
