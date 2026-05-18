"""客户决策摘要与标签服务。"""

from __future__ import annotations

from dataclasses import asdict

from src.models import AgentResult


def derive_overage_status(
    complaint: str,
    customer: dict[str, object] | None,
) -> dict[str, object]:
    """推导是否超套。

    Args:
        complaint: 客户投诉原文。
        customer: 本地客户画像。

    Returns:
        超套状态结构。
    """

    keywords = ("超量", "超套", "流量不够", "月底提醒", "扣费", "流量费")
    complaint_text = str(complaint)
    has_keyword = any(keyword in complaint_text for keyword in keywords)
    source = customer or {}
    plan_data = _as_float(source.get("plan_data_gb"))
    usage_data = _as_float(source.get("last_month_usage_gb"))
    fee_value = _as_float(source.get("overage_fee"))

    status = "未知"
    usage_text = "暂无用量数据"
    fee_text = "暂无超套费用"
    reason = "暂无用量数据，需查询系统详单。"
    if plan_data is not None and usage_data is not None:
        usage_text = f"上月{usage_data:g}G / 套餐{plan_data:g}G"
        if usage_data > plan_data:
            status = "是"
            reason = "上月使用量已超过套餐内流量，建议优先核查超套费用。"
        else:
            status = "否"
            reason = "本地演示用量未超过套餐内流量。"
    if fee_value is not None and fee_value > 0:
        fee_text = f"超套费用{fee_value:g}元"
    if has_keyword and status != "是":
        status = "疑似"
        reason = "投诉内容出现流量或扣费相关表达，建议优先核查详单。"

    label = {
        "是": "已超套",
        "疑似": "疑似超套",
        "否": "未发现超套",
        "未知": "暂无数据",
    }.get(status, "暂无数据")
    return {
        "status": status,
        "label": label,
        "reason": reason,
        "usage_text": usage_text,
        "fee_text": fee_text,
    }


def extract_top_business(result: AgentResult | None) -> dict[str, object]:
    """提取首推业务。

    Args:
        result: 智能体结果。

    Returns:
        首推业务结构。
    """

    if result is None or not result.recommended_policies:
        return {
            "title": "待生成",
            "category": "暂无",
            "price": "",
            "reason": "输入投诉后自动生成推荐业务。",
            "talking_point": "",
            "benefits": [],
            "risk_notes": [],
        }

    top_item = result.recommended_policies[0]
    policy = top_item.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return {
        "title": str(top_item.get("title", policy.get("title", "待生成"))),
        "category": str(policy.get("category", "暂无")),
        "price": str(policy.get("price", "")),
        "reason": str(top_item.get("reason", "")),
        "talking_point": str(top_item.get("talking_point", "")),
        "benefits": _format_list(policy.get("benefits"), limit=4),
        "risk_notes": _format_list(policy.get("risk_notes"), limit=3),
    }


def build_decision_summary(
    result: AgentResult,
    complaint: str,
    customer: dict[str, object] | None,
    profile: dict[str, object],
) -> dict[str, object]:
    """构建前端决策驾驶舱摘要。

    Args:
        result: 智能体结果。
        complaint: 客户投诉原文。
        customer: 本地客户画像。
        profile: 不含手机号的客户画像。

    Returns:
        决策摘要结构。
    """

    analysis = result.customer_analysis
    risk_level = str(analysis.get("risk_level", "中"))
    overage = derive_overage_status(complaint, customer)
    return {
        "overage": overage,
        "top_business": extract_top_business(result),
        "risk_level": risk_level,
        "complaint_type": str(analysis.get("complaint_type", "其他")),
        "emotion": str(analysis.get("emotion", "不满")),
        "follow_priority": default_follow_priority(risk_level),
        "customer_value": customer_value_level(customer, profile),
        "customer_tags": customer_tags(customer, profile, overage),
    }


def customer_value_level(
    customer: dict[str, object] | None,
    profile: dict[str, object],
) -> str:
    """判断客户价值等级。

    Args:
        customer: 本地客户画像。
        profile: 生成接口画像。

    Returns:
        客户价值等级。
    """

    source = customer or profile
    monthly_fee = _as_float(source.get("monthly_fee")) or 0
    tenure_years = _as_float(source.get("tenure_years")) or 0
    if monthly_fee >= 199 or tenure_years >= 5:
        return "高价值"
    if monthly_fee >= 99:
        return "中价值"
    return "普通"


def customer_tags(
    customer: dict[str, object] | None,
    profile: dict[str, object],
    overage_status: dict[str, object],
) -> list[str]:
    """生成客户标签。

    Args:
        customer: 本地客户画像。
        profile: 生成接口画像。
        overage_status: 超套判断结构。

    Returns:
        最多三个客户标签。
    """

    source = customer or profile
    tags: list[str] = []
    if customer_value_level(customer, profile) == "高价值":
        tags.append("高价值")
    if bool(source.get("wants_port_out", False)):
        tags.append("携转风险")
    if overage_status.get("status") in {"是", "疑似"}:
        tags.append("流量超套")
    family_count = _as_float(source.get("family_mobile_count")) or 0
    if family_count >= 2:
        tags.append("家庭融合")
    if bool(source.get("has_broadband", False)):
        tags.append("宽带用户")
    return tags[:3]


def default_follow_status(risk_level: str) -> str:
    """按风险等级生成默认处理状态。"""

    score = risk_score(risk_level)
    if score == 3:
        return "待优先跟进"
    if score == 2:
        return "待跟进"
    return "已生成方案"


def default_follow_priority(risk_level: str) -> str:
    """按风险等级生成默认优先级。"""

    score = risk_score(risk_level)
    if score == 3:
        return "P1"
    if score == 2:
        return "P2"
    return "P3"


def risk_score(risk_level: str) -> int:
    """把风险等级转换为排序分。"""

    mapping = {"高": 3, "中": 2, "低": 1}
    text = str(risk_level).strip()
    if text in mapping:
        return mapping[text]
    for key, score in mapping.items():
        if key in text:
            return score
    return 0


def agent_result_to_dict(result: AgentResult) -> dict[str, object]:
    """把智能体结果转换为可 JSON 序列化字典。"""

    return asdict(result)


def flatten_recommended_policies(
    items: list[dict[str, object]],
) -> list[dict[str, object]]:
    """拍平推荐政策，方便前端直接展示分类、价格和权益。

    Args:
        items: 智能体返回的推荐政策列表。

    Returns:
        保留原始 nested policy，同时补齐顶层展示字段的推荐政策列表。
    """

    flattened: list[dict[str, object]] = []
    for item in items:
        row = dict(item)
        policy = row.get("policy")
        if isinstance(policy, dict):
            row.setdefault("category", policy.get("category", ""))
            row.setdefault("price", policy.get("price", ""))
            row.setdefault("benefits", policy.get("benefits", []))
            row.setdefault("conditions", policy.get("conditions", []))
            row.setdefault("risk_notes", policy.get("risk_notes", []))
        flattened.append(row)
    return flattened


def _format_list(value: object, limit: int | None = None) -> list[str]:
    """把任意字段规范为字符串列表。"""

    if value is None:
        items: list[object] = []
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    formatted = [str(item) for item in items if str(item).strip()]
    if limit is not None:
        return formatted[:limit]
    return formatted


def _as_float(value: object) -> float | None:
    """安全转换为浮点数。"""

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
