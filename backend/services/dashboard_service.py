"""进程内演示看板服务。"""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import datetime

from backend.services.decision_service import default_follow_priority
from backend.services.decision_service import default_follow_status
from backend.services.decision_service import risk_score
from src.models import AgentResult

_RECORDS: list[dict[str, object]] = []
_COMPLAINT_TYPE_COUNTER: Counter[str] = Counter()
_POLICY_COUNTER: Counter[str] = Counter()
_ELAPSED_TOTAL = 0.0
_LLM_SUCCESS_COUNT = 0
_FALLBACK_COUNT = 0

CSV_COLUMNS = [
    "序号",
    "生成时间",
    "手机号",
    "风险等级",
    "跟进优先级",
    "是否超套",
    "推荐业务",
    "投诉类型",
    "客户情绪",
    "客户价值",
    "客户标签",
    "当前月租",
    "客户类型",
    "明确携转",
    "处理状态",
    "模式",
    "耗时",
    "投诉摘要",
]


def add_record(
    result: AgentResult,
    phone: str,
    phone_masked: str,
    complaint: str,
    profile: dict[str, object],
    decision_summary: dict[str, object],
) -> None:
    """新增一条风险队列记录。

    Args:
        result: 智能体结果。
        phone: 标准化手机号，仅内部搜索使用。
        phone_masked: 脱敏手机号。
        complaint: 客户投诉原文。
        profile: 不含手机号的客户画像。
        decision_summary: 决策摘要。

    Returns:
        无返回值。
    """

    global _ELAPSED_TOTAL
    global _FALLBACK_COUNT
    global _LLM_SUCCESS_COUNT

    analysis = result.customer_analysis
    risk_level = str(analysis.get("risk_level", "中"))
    complaint_type = str(analysis.get("complaint_type", "其他"))
    top_business = dict(decision_summary.get("top_business", {}))
    overage = dict(decision_summary.get("overage", {}))
    sequence = len(_RECORDS) + 1

    if result.mode == "llm":
        _LLM_SUCCESS_COUNT += 1
    else:
        _FALLBACK_COUNT += 1
    _ELAPSED_TOTAL += float(result.elapsed_seconds)
    _COMPLAINT_TYPE_COUNTER[complaint_type] += 1
    for item in result.recommended_policies:
        title = str(item.get("title", item.get("policy_id", "未知政策")))
        _POLICY_COUNTER[title] += 1

    _RECORDS.append(
        {
            "sequence": sequence,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "phone_masked": phone_masked,
            "_raw_phone": phone,
            "_profile": dict(profile),
            "_complaint": complaint[:200],
            "complaint_type": complaint_type,
            "risk_level": risk_level,
            "_risk_score": risk_score(risk_level),
            "follow_priority": default_follow_priority(risk_level),
            "overage_label": str(overage.get("label", "暂无数据")),
            "top_business": str(top_business.get("title", "")),
            "emotion": str(analysis.get("emotion", "不满")),
            "customer_value": str(decision_summary.get("customer_value", "普通")),
            "customer_tags": "、".join(
                str(tag) for tag in decision_summary.get("customer_tags", [])
            ),
            "monthly_fee": int(profile.get("monthly_fee", 0)),
            "customer_type": str(profile.get("customer_type", "")),
            "wants_port_out": "是" if profile.get("wants_port_out") else "否",
            "status": default_follow_status(risk_level),
            "mode": "云端模型生成" if result.mode == "llm" else "本地模板兜底",
            "elapsed_seconds": round(float(result.elapsed_seconds), 2),
            "complaint_summary": complaint[:60],
        }
    )


def get_dashboard() -> dict[str, object]:
    """获取风险看板状态。

    Args:
        无参数。

    Returns:
        看板指标、队列和计数器。
    """

    total_cases = len(_RECORDS)
    high_risk_cases = sum(1 for row in _RECORDS if row.get("risk_level") == "高")
    priority_wait_count = sum(
        1 for row in _RECORDS if row.get("status") == "待优先跟进"
    )
    average_elapsed = _ELAPSED_TOTAL / total_cases if total_cases else 0.0
    sorted_records = sorted(
        _RECORDS,
        key=lambda row: (int(row.get("_risk_score", 0)), int(row.get("sequence", 0))),
        reverse=True,
    )
    return {
        "metrics": {
            "total_cases": total_cases,
            "high_risk_cases": high_risk_cases,
            "high_risk_percent": (
                high_risk_cases / total_cases * 100 if total_cases else 0.0
            ),
            "priority_wait_count": priority_wait_count,
            "llm_success_count": _LLM_SUCCESS_COUNT,
            "fallback_count": _FALLBACK_COUNT,
            "average_elapsed": average_elapsed,
        },
        "risk_queue": [_public_record(row) for row in sorted_records],
        "complaint_type_counter": dict(_COMPLAINT_TYPE_COUNTER),
        "policy_counter": dict(_POLICY_COUNTER),
    }


def reset_dashboard() -> None:
    """清空本次演示看板。"""

    global _ELAPSED_TOTAL
    global _FALLBACK_COUNT
    global _LLM_SUCCESS_COUNT

    _RECORDS.clear()
    _COMPLAINT_TYPE_COUNTER.clear()
    _POLICY_COUNTER.clear()
    _ELAPSED_TOTAL = 0.0
    _LLM_SUCCESS_COUNT = 0
    _FALLBACK_COUNT = 0


def export_csv() -> bytes:
    """导出 UTF-8 with BOM CSV。"""

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for record in get_dashboard()["risk_queue"]:
        writer.writerow(
            {
                "序号": record["sequence"],
                "生成时间": record["generated_at"],
                "手机号": record["phone_masked"],
                "风险等级": record["risk_level"],
                "跟进优先级": record["follow_priority"],
                "是否超套": record["overage_label"],
                "推荐业务": record["top_business"],
                "投诉类型": record["complaint_type"],
                "客户情绪": record["emotion"],
                "客户价值": record["customer_value"],
                "客户标签": record["customer_tags"],
                "当前月租": record["monthly_fee"],
                "客户类型": record["customer_type"],
                "明确携转": record["wants_port_out"],
                "处理状态": record["status"],
                "模式": record["mode"],
                "耗时": record["elapsed_seconds"],
                "投诉摘要": record["complaint_summary"],
            }
        )
    return output.getvalue().encode("utf-8-sig")


def _public_record(record: dict[str, object]) -> dict[str, object]:
    """移除内部手机号和排序字段。"""

    public = dict(record)
    public.pop("_raw_phone", None)
    public.pop("_risk_score", None)
    public.pop("_profile", None)
    public.pop("_complaint", None)
    return public


def find_latest_record_by_phone(phone: str) -> dict[str, object] | None:
    """根据完整手机号查询本次风险队列中的最近一条处理记录。

    Args:
        phone: 标准化或原始手机号。

    Returns:
        最近一条内部记录；未命中时返回 None。
    """

    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return None
    for record in reversed(_RECORDS):
        if _normalize_phone(record.get("_raw_phone")) == normalized_phone:
            return dict(record)
    return None


def build_customer_view_from_record(record: dict[str, object]) -> dict[str, object]:
    """把风险队列历史记录转换成前端 Customer 结构。

    Args:
        record: 内部风险队列记录。

    Returns:
        不含完整手机号的客户画像视图。
    """

    profile = record.get("_profile")
    if not isinstance(profile, dict):
        profile = {}
    phone_masked = str(record.get("phone_masked", "未填写"))
    raw_phone = _normalize_phone(record.get("_raw_phone"))
    recent_count = sum(
        1
        for item in _RECORDS
        if raw_phone and _normalize_phone(item.get("_raw_phone")) == raw_phone
    )
    complaint_type = str(record.get("complaint_type", "其他"))
    top_business = str(record.get("top_business", ""))
    return {
        "phone_masked": phone_masked,
        "customer_name": "本次处理客户",
        "monthly_fee": _as_int(profile.get("monthly_fee"), 0),
        "customer_type": str(profile.get("customer_type", "存量")),
        "tenure_years": _as_float(profile.get("tenure_years"), 0),
        "has_broadband": bool(profile.get("has_broadband", False)),
        "wants_device": bool(profile.get("wants_device", False)),
        "family_mobile_count": _as_int(profile.get("family_mobile_count"), 1),
        "wants_port_out": bool(profile.get("wants_port_out", False)),
        "plan_name": "",
        "plan_data_gb": None,
        "last_month_usage_gb": None,
        "overage_fee": None,
        "recent_complaint_count": recent_count,
        "recommended_hint": f"本次看板记录：{complaint_type}，首推 {top_business}",
        "source": "dashboard_history",
        "last_complaint_summary": str(record.get("complaint_summary", "")),
        "last_risk_level": str(record.get("risk_level", "")),
        "last_top_business": top_business,
        "last_status": str(record.get("status", "")),
    }


def _normalize_phone(raw: object) -> str:
    """标准化手机号，仅用于后端内存匹配。"""

    if raw is None:
        return ""
    return str(raw).replace(" ", "").replace("-", "").strip()


def _as_int(value: object, default: int) -> int:
    """安全转换为整数。"""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: object, default: float) -> float:
    """安全转换为浮点数。"""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default
