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
    "是否超耗",
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
            "generated_at": datetime.now().strftime("%H:%M:%S"),
            "phone_masked": phone_masked,
            "_raw_phone": phone,
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
                "是否超耗": record["overage_label"],
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
    return public
