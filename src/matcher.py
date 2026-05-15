"""本地政策候选召回与打分。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.models import CustomerProfile
from src.models import PolicyMatch

CHURN_KEYWORDS = ("携转", "离网", "换别家", "不用了", "转网", "携号转网")
BROADBAND_KEYWORDS = ("宽带", "WiFi", "wifi", "网速", "卡顿", "上网课")
DEVICE_KEYWORDS = ("手机", "换机", "购机", "终端", "分期")
BUSINESS_KEYWORDS = ("商客", "商户", "门店", "宣传", "工作号", "AI监控")


def load_policies(path: str | Path) -> list[dict[str, object]]:
    """加载本地政策库。

    Args:
        path: 政策库 JSON 文件路径。

    Returns:
        政策卡字典列表。
    """

    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as file:
        policies = json.load(file)
    if not isinstance(policies, list):
        raise ValueError("政策库必须是 JSON 数组。")
    return policies


def match_policies(
    complaint: str,
    profile: CustomerProfile,
    policies: list[dict[str, object]],
    top_k: int = 5,
) -> list[PolicyMatch]:
    """按规则召回最匹配的政策候选。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像。
        policies: 政策卡列表。
        top_k: 返回候选数量。

    Returns:
        按分数降序排列的政策候选。
    """

    matches = []
    for policy in policies:
        score, reasons = _score_policy(complaint, profile, policy)
        if not reasons:
            reasons = ["作为兜底候选，便于 LLM 在政策范围内选择。"]
        matches.append(
            PolicyMatch(
                policy_id=str(policy.get("id", "")),
                title=str(policy.get("title", "")),
                score=score,
                reasons=_deduplicate(reasons),
                policy=policy,
            )
        )

    matches.sort(key=lambda match: (-match.score, match.policy_id))
    return matches[:top_k]


def _score_policy(
    complaint: str,
    profile: CustomerProfile,
    policy: dict[str, object],
) -> tuple[int, list[str]]:
    """计算单张政策卡的匹配分。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像。
        policy: 单张政策卡。

    Returns:
        匹配分和匹配原因。
    """

    score = 0
    reasons: list[str] = []
    keyword_hits = _keyword_hits(complaint, policy.get("keywords", []))
    if keyword_hits:
        score += min(len(keyword_hits) * 8, 40)
        reasons.append(f"命中关键词：{'、'.join(keyword_hits)}")

    is_high_risk = profile.wants_port_out or _contains_any(
        complaint, CHURN_KEYWORDS
    )
    if is_high_risk and _is_retention_policy(policy):
        score += 25
        reasons.append("客户明确有离网或携转风险，适合保有类政策。")

    if profile.monthly_fee <= 39 and _is_flow_or_upgrade_policy(policy):
        score += 20
        reasons.append("当前套餐较低，适合大流量或升档方案。")

    if profile.monthly_fee >= 119 and (
        _is_retention_policy(policy) or _is_broadband_policy(policy)
    ):
        score += 20
        reasons.append("当前套餐在中高档位，适合保有或宽带融合方案。")

    if profile.has_broadband or _contains_any(complaint, BROADBAND_KEYWORDS):
        if _is_broadband_policy(policy):
            score += 25
            reasons.append("客户涉及宽带或网络质量诉求。")

    if profile.wants_device or _contains_any(complaint, DEVICE_KEYWORDS):
        if _is_device_policy(policy):
            score += 30
            reasons.append("客户有换机或购机需求，适合终端方案。")

    if profile.customer_type == "商客" or _contains_any(complaint, BUSINESS_KEYWORDS):
        if _is_business_policy(policy):
            score += 30
            reasons.append("客户为商客或门店场景，适合商客融合方案。")

    if profile.family_mobile_count >= 3 and _is_family_policy(policy):
        score += 20
        reasons.append("家庭号码较多，适合家庭融合或亲情网方案。")

    if profile.tenure_years >= 5 and _is_retention_policy(policy):
        score += 15
        reasons.append("客户网龄较长，可突出老客户保有权益。")

    if is_high_risk and _is_retention_policy(policy):
        score += 15
        reasons.append("风险等级较高，优先补充返费和保有抓手。")

    adjustment, adjustment_reason = _eligibility_adjustment(profile, policy)
    score += adjustment
    if adjustment_reason:
        reasons.append(adjustment_reason)

    return score, reasons


def _keyword_hits(complaint: str, keywords: object) -> list[str]:
    """提取投诉命中的政策关键词。

    Args:
        complaint: 客户投诉原文。
        keywords: 政策关键词字段。

    Returns:
        已命中的关键词列表。
    """

    if not isinstance(keywords, list):
        return []
    hits = []
    normalized = complaint.casefold()
    for keyword in keywords:
        keyword_text = str(keyword)
        if keyword_text and keyword_text.casefold() in normalized:
            hits.append(keyword_text)
    return _deduplicate(hits)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    """判断文本是否包含任意关键词。

    Args:
        text: 待检索文本。
        keywords: 关键词集合。

    Returns:
        命中任意关键词时返回 True。
    """

    normalized = text.casefold()
    return any(keyword.casefold() in normalized for keyword in keywords)


def _policy_search_text(policy: dict[str, object]) -> str:
    """合并政策字段，便于做轻量规则判断。

    Args:
        policy: 单张政策卡。

    Returns:
        合并后的搜索文本。
    """

    fields = [
        policy.get("id", ""),
        policy.get("title", ""),
        policy.get("category", ""),
        policy.get("target", ""),
        policy.get("script_hint", ""),
    ]
    return " ".join(str(field) for field in fields)


def _is_retention_policy(policy: dict[str, object]) -> bool:
    """判断是否为保有或返费政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于保有或返费政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("保有", "返费", "无忧包", "老客户"))


def _is_flow_or_upgrade_policy(policy: dict[str, object]) -> bool:
    """判断是否为流量、低资费或升档政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于流量或升档政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("流量", "低资费", "升档", "畅玩"))


def _is_broadband_policy(policy: dict[str, object]) -> bool:
    """判断是否为宽带相关政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于宽带相关政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("宽带", "FTTR", "WiFi", "全家享"))


def _is_device_policy(policy: dict[str, object]) -> bool:
    """判断是否为终端换机政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于终端或换机政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("终端", "换机", "购机", "手机"))


def _is_family_policy(policy: dict[str, object]) -> bool:
    """判断是否为家庭融合政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于家庭或亲情网政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("家庭", "亲情", "全家享", "副号"))


def _is_business_policy(policy: dict[str, object]) -> bool:
    """判断是否为商客融合政策。

    Args:
        policy: 单张政策卡。

    Returns:
        属于商客政策时返回 True。
    """

    text = _policy_search_text(policy)
    return _contains_any(text, ("商客", "商户", "门店", "慧商", "AI企计划"))


def _eligibility_adjustment(
    profile: CustomerProfile,
    policy: dict[str, object],
) -> tuple[int, str]:
    """按政策典型门槛修正候选分。

    Args:
        profile: 客户画像。
        policy: 单张政策卡。

    Returns:
        分数修正值和说明。
    """

    policy_id = str(policy.get("id", ""))
    if policy_id == "P04" and profile.monthly_fee < 199:
        return -35, "当前套餐未达到 P04 典型门槛，仅建议作为备选核查。"
    if policy_id == "P05" and profile.monthly_fee < 119:
        return -30, "当前套餐未达到 P05 典型门槛，仅建议作为备选核查。"
    return 0, ""


def _deduplicate(values: Iterable[str]) -> list[str]:
    """按原始顺序去重。

    Args:
        values: 待去重字符串集合。

    Returns:
        去重后的字符串列表。
    """

    result = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
