"""客户拯救者冒烟测试脚本。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import src.agent as agent_module
from app import _derive_overage_status
from app import _extract_top_business
from app import _mask_phone
from app import _normalize_phone
from app import _risk_score
from src.matcher import match_policies
from src.models import CustomerProfile

DATA_DIR = ROOT_DIR / "data"


def main() -> None:
    """执行不依赖 Streamlit 启动的基础冒烟测试。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    policies = _load_json_list(DATA_DIR / "policies.json")
    demo_cases = _load_json_list(DATA_DIR / "demo_cases.json")
    customers = _load_json_list(DATA_DIR / "customers.json")
    _assert(len(policies) >= 12, "policies.json 至少需要 12 条政策。")
    _assert(len(demo_cases) >= 6, "demo_cases.json 至少需要 6 条案例。")
    _assert(len(customers) >= 6, "customers.json 至少需要 6 条演示客户。")
    _assert(
        _normalize_phone("138-0013-8000") == "13800138000",
        "手机号标准化必须去掉短横线。",
    )
    _assert(
        _mask_phone("13800138000") == "138****8000",
        "手机号脱敏格式不正确。",
    )
    _assert(
        _risk_score("高") > _risk_score("中") > _risk_score("低"),
        "风险排序必须满足高大于中大于低。",
    )
    overage = _derive_overage_status(
        "",
        {"plan_data_gb": 80, "last_month_usage_gb": 96, "overage_fee": 18},
    )
    _assert(overage["status"] == "是", "已超出套餐流量时必须标记为已超耗。")
    suspected_overage = _derive_overage_status("月底老是提醒超量", None)
    _assert(
        suspected_overage["status"] == "疑似",
        "投诉包含超量表达时必须标记为疑似超耗。",
    )
    top_business = _extract_top_business(None)
    _assert(top_business["title"] == "待生成", "空结果首推业务必须可安全占位。")
    _assert(
        all(bool(case.get("phone")) for case in demo_cases),
        "所有演示案例都需要包含 phone 字段。",
    )

    first_case = demo_cases[0]
    _assert(bool(first_case.get("phone")), "演示案例需要包含 phone 字段。")
    profile_data = first_case.get("profile", {})
    _assert(isinstance(profile_data, dict), "演示案例 profile 必须是对象。")
    profile = CustomerProfile(**profile_data)
    complaint = str(first_case.get("complaint", ""))

    matches = match_policies(complaint, profile, policies, top_k=5)
    _assert(len(matches) == 5, "match_policies 必须返回 Top 5。")

    _clear_api_keys()
    result = agent_module.ClientSaviorAgent(policies).run(
        complaint=complaint,
        profile=profile,
        use_llm=True,
    )
    _assert(result.mode == "fallback", "未配置 API Key 时必须自动兜底。")
    _assert(bool(result.customer_analysis), "结果必须包含 customer_analysis。")
    _assert(bool(result.recommended_policies), "结果必须包含 recommended_policies。")
    _assert(bool(result.retention_script), "结果必须包含 retention_script。")
    _assert(bool(result.internal_notes), "结果必须包含 internal_notes。")

    mock_case = demo_cases[1]
    mock_profile_data = mock_case.get("profile", {})
    _assert(isinstance(mock_profile_data, dict), "mock 案例 profile 必须是对象。")
    mock_profile = CustomerProfile(**mock_profile_data)
    _run_mock_llm_success_test(
        policies,
        str(mock_case.get("complaint", "")),
        mock_profile,
    )

    print("smoke_test_ok")


def _run_mock_llm_success_test(
    policies: list[dict[str, object]],
    complaint: str,
    profile: CustomerProfile,
) -> None:
    """验证 mock LLM 成功链路和中文排序解析。

    Args:
        policies: 政策卡列表。
        complaint: 客户投诉原文。
        profile: 客户画像。

    Returns:
        无返回值。
    """

    original_is_llm_configured = agent_module.is_llm_configured
    original_generate_with_llm = agent_module.generate_with_llm
    try:
        agent_module.is_llm_configured = lambda: True
        agent_module.generate_with_llm = _fake_generate_with_llm
        result = agent_module.ClientSaviorAgent(policies).run(
            complaint=complaint,
            profile=profile,
            use_llm=True,
        )
        _assert(result.mode == "llm", "mock LLM 成功时 mode 必须为 llm。")
        _assert(result.model == "mock-qwen", "mock LLM 模型名不正确。")
        _assert(
            result.customer_analysis["complaint_type"] == "流量不足",
            "mock LLM 客户分析未生效。",
        )
        _assert(
            len(result.recommended_policies) >= 1,
            "mock LLM 必须返回推荐政策。",
        )
        _assert(
            result.recommended_policies[0]["policy_id"] == "P01",
            "mock LLM 推荐的 P01 必须被保留。",
        )
        _assert(
            result.recommended_policies[0]["rank"] == 1,
            "中文 rank 必须被解析为数字 1。",
        )
        _assert(result.llm_error is None, "mock LLM 成功不应有错误摘要。")
    finally:
        agent_module.is_llm_configured = original_is_llm_configured
        agent_module.generate_with_llm = original_generate_with_llm


def _fake_generate_with_llm(
    complaint: str,
    profile: dict[str, object],
    candidate_policies: list[dict[str, object]],
) -> dict[str, object]:
    """返回固定 mock LLM 结果。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        candidate_policies: 候选政策列表。

    Returns:
        与真实 LLM 函数一致的响应结构。
    """

    del complaint, profile, candidate_policies
    return {
        "result": {
            "customer_analysis": {
                "complaint_type": "流量不足",
                "emotion": "不满",
                "risk_level": "中",
                "key_needs": ["流量不够", "资费可控"],
                "summary": "客户希望在不明显涨价的情况下解决流量不足。",
            },
            "recommended_policies": [
                {
                    "policy_id": "P01",
                    "rank": "第一",
                    "reason": "客户对价格敏感且反馈流量不够。",
                    "talking_point": "优先用低月租大流量方案解决刷视频超量问题。",
                }
            ],
            "retention_script": {
                "opening": "您好，看到您主要是流量不够，我先帮您按低成本方向核查。",
                "solution": "可以优先看39元新潮玩乐享卡或相近大流量方案，尽量控制月租变化。",
                "risk_disclosure": "办理资格、优惠期、首充和后续资费以系统办理结果为准。",
                "next_step": "我先帮您查一下当前号码是否满足办理条件。",
            },
            "internal_notes": ["先核查是否有互斥合约。"],
        },
        "elapsed_seconds": 0.12,
        "model": "mock-qwen",
        "cached": False,
    }


def _load_json_list(path: Path) -> list[dict[str, object]]:
    """读取 JSON 数组文件。

    Args:
        path: JSON 文件路径。

    Returns:
        JSON 对象列表。
    """

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    _assert(isinstance(data, list), f"{path.name} 必须是 JSON 数组。")
    return data


def _clear_api_keys() -> None:
    """清除当前进程中的 API Key，验证本地兜底。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    os.environ["DASHSCOPE_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""


def _assert(condition: bool, message: str) -> None:
    """抛出带中文信息的断言错误。

    Args:
        condition: 断言条件。
        message: 失败信息。

    Returns:
        无返回值。

    Raises:
        AssertionError: 条件不满足时抛出。
    """

    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    main()
