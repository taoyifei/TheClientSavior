"""客户拯救者 FastAPI 后端入口。"""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.schemas import CustomerLookupResponse  # noqa: E402
from backend.schemas import DashboardResponse  # noqa: E402
from backend.schemas import GenerateRequest  # noqa: E402
from backend.schemas import GenerateResponse  # noqa: E402
from backend.services import dashboard_service  # noqa: E402
from backend.services.customer_service import find_customer_by_phone  # noqa: E402
from backend.services.customer_service import mask_phone  # noqa: E402
from backend.services.customer_service import normalize_phone  # noqa: E402
from backend.services.customer_service import public_customer_view  # noqa: E402
from backend.services.data_service import load_demo_cases  # noqa: E402
from backend.services.data_service import load_policies  # noqa: E402
from backend.services.decision_service import build_decision_summary  # noqa: E402
from backend.services.decision_service import flatten_recommended_policies  # noqa: E402
from src.agent import ClientSaviorAgent  # noqa: E402
from src.llm_client import get_llm_settings  # noqa: E402
from src.llm_client import is_llm_configured  # noqa: E402
from src.llm_client import test_llm_connection  # noqa: E402
from src.models import CustomerProfile  # noqa: E402

app = FastAPI(title="The Client Savior API")
allowed_origin_regex = (
    r"^http://("
    r"localhost|127\.0\.0\.1|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r"):(5173|4173)$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """返回后端健康状态。"""

    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, object]:
    """返回前端可见的 LLM 配置。"""

    settings = get_llm_settings()
    return {
        "llm_configured": is_llm_configured(),
        "model": settings["model"],
        "timeout": settings["timeout"],
        "base_url": settings["base_url"],
    }


@app.post("/api/llm/test")
def test_llm() -> dict[str, object]:
    """执行 LLM 连通性测试。"""

    try:
        result = test_llm_connection()
        return {
            "ok": True,
            "elapsed_seconds": result["elapsed_seconds"],
            "model": result["model"],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


@app.get("/api/policies")
def policies() -> list[dict[str, object]]:
    """返回政策库。"""

    return load_policies()


@app.get("/api/demo-cases")
def demo_cases() -> list[dict[str, object]]:
    """返回演示案例。"""

    return load_demo_cases()


@app.get("/api/customers/lookup", response_model=CustomerLookupResponse)
def lookup_customer(phone: str = Query(default="")) -> CustomerLookupResponse:
    """按手机号查询本地演示客户。"""

    normalized_phone = normalize_phone(phone)
    customer = find_customer_by_phone(normalized_phone)
    if customer is None:
        return CustomerLookupResponse(
            found=False,
            customer=None,
            message="未查询到客户画像，可手动补充画像。",
        )
    return CustomerLookupResponse(
        found=True,
        customer=public_customer_view(customer),
        message="命中客户画像。",
    )


@app.post("/api/generate", response_model=GenerateResponse)
def generate(request: GenerateRequest) -> GenerateResponse:
    """生成客户挽留方案。"""

    complaint = request.complaint.strip()
    if not complaint:
        raise HTTPException(status_code=400, detail="投诉内容不能为空。")

    normalized_phone = normalize_phone(request.phone)
    phone_masked = mask_phone(normalized_phone)
    customer = find_customer_by_phone(normalized_phone) if normalized_phone else None
    # 兼容 Pydantic v1/v2，避免不同本机环境下请求体转换失败。
    if hasattr(request.profile, "model_dump"):
        profile_dict = request.profile.model_dump()
    else:
        profile_dict = request.profile.dict()
    profile = CustomerProfile(**profile_dict)

    result = ClientSaviorAgent(load_policies()).run(
        complaint=complaint,
        profile=profile,
        use_llm=request.use_llm,
    )
    decision_summary = build_decision_summary(
        result=result,
        complaint=complaint,
        customer=customer,
        profile=profile_dict,
    )
    dashboard_service.add_record(
        result=result,
        phone=normalized_phone,
        phone_masked=phone_masked,
        complaint=complaint,
        profile=profile_dict,
        decision_summary=decision_summary,
    )

    payload = asdict(result)
    payload["recommended_policies"] = flatten_recommended_policies(
        payload["recommended_policies"]
    )
    payload["phone_masked"] = phone_masked
    payload["decision_summary"] = decision_summary
    return GenerateResponse(**payload)


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard() -> DashboardResponse:
    """返回本次演示风险看板。"""

    return DashboardResponse(**dashboard_service.get_dashboard())


@app.post("/api/dashboard/reset")
def reset_dashboard() -> dict[str, bool]:
    """清空本次演示风险看板。"""

    dashboard_service.reset_dashboard()
    return {"ok": True}


@app.get("/api/dashboard/export")
def export_dashboard() -> Response:
    """导出客户风险队列 CSV。"""

    return Response(
        content=dashboard_service.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; filename=client_savior_risk_queue.csv"
            )
        },
    )
