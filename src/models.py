"""客户拯救者的数据模型。"""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerProfile:
    """客户画像输入。

    Args:
        monthly_fee: 当前套餐月租。
        customer_type: 客户类型。
        tenure_years: 网龄年数。
        has_broadband: 是否已有宽带。
        wants_device: 是否有换机需求。
        family_mobile_count: 家庭移动号码数量。
        wants_port_out: 是否明确有携转或离网意向。

    Returns:
        客户画像数据对象。
    """

    monthly_fee: int
    customer_type: str
    tenure_years: float
    has_broadband: bool
    wants_device: bool
    family_mobile_count: int
    wants_port_out: bool

    def to_dict(self) -> dict[str, object]:
        """转换为普通字典，便于传给 LLM 和 Streamlit。

        Args:
            无参数。

        Returns:
            当前画像的字典表示。
        """

        return asdict(self)


@dataclass(frozen=True)
class PolicyMatch:
    """本地政策召回结果。

    Args:
        policy_id: 政策编号。
        title: 政策名称。
        score: 本地匹配分。
        reasons: 本地匹配原因。
        policy: 原始政策卡数据。

    Returns:
        政策召回数据对象。
    """

    policy_id: str
    title: str
    score: int
    reasons: list[str]
    policy: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        """转换为页面可直接渲染的字典。

        Args:
            无参数。

        Returns:
            包含分数、原因和政策详情的字典。
        """

        return asdict(self)


@dataclass(frozen=True)
class AgentResult:
    """智能体统一输出。

    Args:
        mode: 生成模式，取值为 ``llm`` 或 ``fallback``。
        model: 当前配置的模型名称。
        elapsed_seconds: 本次生成耗时。
        cached: 是否命中 LLM 缓存。
        customer_analysis: 客户分析结构。
        recommended_policies: 推荐政策列表。
        retention_script: 挽留话术结构。
        internal_notes: 一线人员内部提醒。
        local_matches: 本地候选召回列表。
        llm_error: LLM 调用错误摘要。

    Returns:
        智能体统一输出对象。
    """

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
