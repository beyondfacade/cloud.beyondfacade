from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from apps.admin.adapter.inbound.api.error_handlers import admin_error_handler
from apps.admin.adapter.inbound.api.v1.access_event_router import router as access_event_router
from apps.admin.adapter.inbound.api.v1.admin_audit_router import router as admin_audit_router
from apps.admin.adapter.inbound.api.v1.admin_session_router import router as admin_session_router
from apps.admin.adapter.inbound.api.v1.admin_user_router import router as admin_user_router
from apps.admin.adapter.inbound.api.v1.access_rule_router import router as access_rule_router
from apps.admin.adapter.inbound.api.v1.ip_block_router import router as ip_block_router
from apps.admin.adapter.inbound.api.v1.security_setting_router import router as security_setting_router
from apps.admin.adapter.inbound.middleware.security_middleware import SecurityMiddleware
from apps.admin.app.errors import AdminError
from apps.childcare.adapter.inbound.api.v1.childcare_center_router import (
    router as childcare_center_router,
)
from apps.childcare.adapter.inbound.api.v1.childcare_center_stat_router import (
    router as childcare_center_stat_router,
)
from apps.convenience.adapter.inbound.api.v1.convenience_store_router import (
    router as convenience_store_router,
)
from apps.finance.adapter.inbound.api.v1.finance_router import router as finance_router
from apps.funding.adapter.inbound.api.v1.funding_program_router import (
    router as funding_router,
)
from apps.agent.adapter.inbound.api.v1.analysis_router import router as analysis_router
from apps.intent.adapter.inbound.api.v1.intent_router import router as intent_router
from apps.master.adapter.inbound.api.v1.region_router import router as region_router
from apps.metric.adapter.inbound.api.v1.region_industry_hour_gap_router import (
    router as hour_gap_router,
)
from apps.metric.adapter.inbound.api.v1.region_industry_metric_router import (
    router as metric_router,
)
from apps.metric.adapter.inbound.api.v1.region_profile_router import (
    router as region_profile_router,
)
from apps.neighborhood.adapter.inbound.api.v1.region_commerce_change_router import (
    router as commerce_change_router,
)
from apps.news.adapter.inbound.api.v1.news_article_router import router as news_router
from apps.ops.adapter.inbound.api.error_handlers import ops_error_handler
from apps.ops.adapter.inbound.api.v1.facility_router import router as facility_router
from apps.ops.adapter.inbound.api.v1.healthcare_router import router as healthcare_router
from apps.ops.app.errors import OpsError
from apps.shock.adapter.inbound.api.v1.event_analog_router import router as event_analog_router
from apps.shock.adapter.inbound.api.v1.shock_event_router import router as shock_router
from apps.store.adapter.inbound.api.v1.store_router import router as store_router
from apps.verdict.adapter.inbound.api.v1.region_industry_verdict_router import (
    router as verdict_router,
)

app = FastAPI(title="beyondfacade backend")
app.add_exception_handler(AdminError, admin_error_handler)
app.add_exception_handler(OpsError, ops_error_handler)
app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3200", "http://127.0.0.1:3200"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # /regions/geojson 등 대형 응답 압축
app.include_router(admin_session_router)
app.include_router(access_event_router)
app.include_router(admin_audit_router)
app.include_router(ip_block_router)
app.include_router(security_setting_router)
app.include_router(access_rule_router)
app.include_router(admin_user_router)
app.include_router(healthcare_router)
app.include_router(facility_router)
app.include_router(analysis_router)
app.include_router(childcare_center_router)
app.include_router(childcare_center_stat_router)
app.include_router(convenience_store_router)
app.include_router(finance_router)
app.include_router(funding_router)
app.include_router(intent_router)
app.include_router(region_router)
app.include_router(metric_router)
app.include_router(region_profile_router)
app.include_router(hour_gap_router)
app.include_router(commerce_change_router)
app.include_router(news_router)
app.include_router(shock_router)
app.include_router(event_analog_router)
app.include_router(store_router)
app.include_router(verdict_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
