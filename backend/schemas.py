"""FastAPI 请求与响应模型。"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class CustomerProfileIn(BaseModel):
    """前端提交的客户画像，不包含手机号。"""

    monthly_fee: int = Field(ge=0)
    customer_type: str
    tenure_years: float = Field(ge=0)
    has_broadband: bool
    wants_device: bool
    family_mobile_count: int = Field(ge=0)
    wants_port_out: bool


class GenerateRequest(BaseModel):
    """生成客户挽留方案的请求体。"""

    phone: str = ""
    complaint: str
    profile: CustomerProfileIn
    use_llm: bool = True


class TopBusiness(BaseModel):
    """首推业务摘要。"""

    title: str
    category: str = ""
    price: str = ""
    reason: str = ""
    talking_point: str = ""
    benefits: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


class OverageStatus(BaseModel):
    """超耗判断结果。"""

    status: str
    label: str
    reason: str
    usage_text: str
    fee_text: str


class DecisionSummary(BaseModel):
    """前端驾驶舱展示用决策摘要。"""

    overage: OverageStatus
    top_business: TopBusiness
    risk_level: str
    complaint_type: str
    emotion: str
    follow_priority: str
    customer_value: str
    customer_tags: list[str]


class CustomerLookupResponse(BaseModel):
    """本地客户查询响应。"""

    found: bool
    customer: dict[str, object] | None = None
    message: str = ""


class GenerateResponse(BaseModel):
    """智能体生成响应。"""

    phone_masked: str
    mode: str
    model: str
    elapsed_seconds: float
    cached: bool
    customer_analysis: dict[str, object]
    recommended_policies: list[dict[str, object]]
    retention_script: dict[str, str]
    internal_notes: list[str]
    local_matches: list[dict[str, object]]
    llm_error: str | None = None
    decision_summary: DecisionSummary


class DashboardRecord(BaseModel):
    """后台风险队列单条记录。"""

    sequence: int
    generated_at: str
    phone_masked: str
    complaint_type: str
    risk_level: str
    follow_priority: str
    overage_label: str
    top_business: str
    emotion: str
    customer_value: str
    customer_tags: str
    monthly_fee: int
    customer_type: str
    wants_port_out: str
    status: str
    mode: str
    elapsed_seconds: float
    complaint_summary: str


class DashboardResponse(BaseModel):
    """后台风险看板响应。"""

    metrics: dict[str, object]
    risk_queue: list[DashboardRecord]
    complaint_type_counter: dict[str, int]
    policy_counter: dict[str, int]
