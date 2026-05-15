"""本地兜底话术模板。"""

from __future__ import annotations

from src.models import PolicyMatch


def build_fallback_result(
    complaint: str,
    profile: dict[str, object],
    matches: list[PolicyMatch],
) -> dict[str, object]:
    """生成与 LLM 输出结构一致的本地兜底结果。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        matches: 本地候选政策。

    Returns:
        结构化客户分析、推荐政策、话术和内部提醒。
    """

    analysis = _analyze_locally(complaint, profile)
    top_matches = matches[:3]
    recommended_policies = []
    for index, match in enumerate(top_matches, start=1):
        recommended_policies.append(
            {
                "policy_id": match.policy_id,
                "rank": index,
                "reason": _build_local_reason(match, analysis),
                "talking_point": str(
                    match.policy.get("script_hint", "结合客户诉求做匹配推荐。")
                ),
            }
        )

    first_policy = top_matches[0] if top_matches else None
    second_policy = top_matches[1] if len(top_matches) > 1 else None
    script = _build_script(analysis, profile, first_policy, second_policy)
    return {
        "customer_analysis": analysis,
        "recommended_policies": recommended_policies,
        "retention_script": script,
        "internal_notes": _build_internal_notes(top_matches),
    }


def _analyze_locally(
    complaint: str,
    profile: dict[str, object],
) -> dict[str, object]:
    """用轻量规则生成客户分析。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。

    Returns:
        客户分析结构。
    """

    complaint_type = _detect_complaint_type(complaint, profile)
    risk_level = _detect_risk_level(complaint, profile, complaint_type)
    emotion = _detect_emotion(complaint, risk_level)
    key_needs = _detect_key_needs(complaint, profile, complaint_type)
    return {
        "complaint_type": complaint_type,
        "emotion": emotion,
        "risk_level": risk_level,
        "key_needs": key_needs,
        "summary": f"客户主要关注{complaint_type}，需要快速给出可核验、可办理的解决方向。",
    }


def _detect_complaint_type(
    complaint: str,
    profile: dict[str, object],
) -> str:
    """识别主投诉类型。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。

    Returns:
        主投诉类型。
    """

    if _contains_any(complaint, ("携转", "离网", "换别家", "转网")):
        return "离网风险"
    if bool(profile.get("wants_device")) or _contains_any(
        complaint, ("手机", "换机", "购机", "分期", "终端")
    ):
        return "换机需求"
    if str(profile.get("customer_type", "")) == "商客" or _contains_any(
        complaint, ("商客", "商户", "门店", "宣传", "工作号", "AI监控")
    ):
        return "商客需求"
    if _contains_any(complaint, ("宽带", "WiFi", "wifi", "卡", "网速", "上网课")):
        return "宽带质量"
    if int(profile.get("family_mobile_count", 0)) >= 3 or _contains_any(
        complaint, ("家庭", "家人", "亲情", "副号", "省钱")
    ):
        return "家庭融合"
    if _contains_any(complaint, ("贵", "优惠", "便宜", "返费", "不公平")):
        return "资费争议"
    if _contains_any(complaint, ("流量", "不够", "刷视频", "超量")):
        return "流量不足"
    return "其他"


def _detect_risk_level(
    complaint: str,
    profile: dict[str, object],
    complaint_type: str,
) -> str:
    """识别挽留风险等级。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        complaint_type: 主投诉类型。

    Returns:
        风险等级。
    """

    if bool(profile.get("wants_port_out")) or _contains_any(
        complaint, ("携转", "转网", "换别家", "不用了")
    ):
        return "高"
    if complaint_type == "资费争议" and int(profile.get("monthly_fee", 0)) >= 119:
        return "高"
    if complaint_type in ("宽带质量", "换机需求", "商客需求", "家庭融合"):
        return "中"
    return "低"


def _detect_emotion(complaint: str, risk_level: str) -> str:
    """识别客户情绪。

    Args:
        complaint: 客户投诉原文。
        risk_level: 风险等级。

    Returns:
        客户情绪标签。
    """

    if risk_level == "高" or _contains_any(complaint, ("没法用", "太差", "投诉")):
        return "强烈不满"
    if _contains_any(complaint, ("贵", "卡", "不够", "优惠")):
        return "不满"
    return "平稳"


def _detect_key_needs(
    complaint: str,
    profile: dict[str, object],
    complaint_type: str,
) -> list[str]:
    """提取关键诉求。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        complaint_type: 主投诉类型。

    Returns:
        关键诉求列表。
    """

    needs = [complaint_type]
    if bool(profile.get("wants_port_out")):
        needs.append("降低离网风险")
    if bool(profile.get("wants_device")):
        needs.append("换机或购机优惠")
    if int(profile.get("family_mobile_count", 0)) >= 3:
        needs.append("家庭号码融合")
    if str(profile.get("customer_type", "")) == "商客":
        needs.append("商客融合能力")
    if _contains_any(complaint, ("贵", "优惠", "便宜", "返费")):
        needs.append("资费优惠")
    return _deduplicate(needs)


def _build_local_reason(
    match: PolicyMatch,
    analysis: dict[str, object],
) -> str:
    """拼接本地推荐理由。

    Args:
        match: 本地政策候选。
        analysis: 客户分析结构。

    Returns:
        推荐理由。
    """

    key_need = str(analysis.get("complaint_type", "客户诉求"))
    reason = match.reasons[0] if match.reasons else "本地规则匹配度较高。"
    return f"该政策与{key_need}相关，{reason}"


def _build_script(
    analysis: dict[str, object],
    profile: dict[str, object],
    first_policy: PolicyMatch | None,
    second_policy: PolicyMatch | None,
) -> dict[str, str]:
    """生成本地兜底话术。

    Args:
        analysis: 客户分析结构。
        profile: 客户画像字典。
        first_policy: 第一推荐政策。
        second_policy: 第二推荐政策。

    Returns:
        四段式挽留话术。
    """

    complaint_type = str(analysis.get("complaint_type", "当前问题"))
    first_title = first_policy.title if first_policy else "适配政策"
    first_hint = (
        str(first_policy.policy.get("script_hint", "先解决客户最紧迫的问题。"))
        if first_policy
        else "先解决客户最紧迫的问题。"
    )
    second_title = second_policy.title if second_policy else "备选方案"
    monthly_fee = int(profile.get("monthly_fee", 0))
    return {
        "opening": (
            f"您好，刚刚看到您反馈的情况，主要集中在{complaint_type}。"
            "我先帮您按当前套餐和使用情况梳理可办方向。"
        ),
        "solution": (
            f"结合您当前约{monthly_fee}元套餐，优先建议核查{first_title}。"
            f"{first_hint} 如您希望多一个选择，也可以同步看{second_title}。"
        ),
        "risk_disclosure": (
            "办理前需要确认客户标签、合约、首充、预存、优惠期和覆盖条件，"
            "具体资格以系统办理结果为准。"
        ),
        "next_step": "如果您方便，我可以先按这个方向帮您核查资格和可办理口径。",
    }


def _build_internal_notes(matches: list[PolicyMatch]) -> list[str]:
    """生成一线人员内部提醒。

    Args:
        matches: 推荐政策候选。

    Returns:
        内部提醒列表。
    """

    notes = ["当前结果由本地规则模板生成，建议一线人员办理前复核客户标签。"]
    for match in matches:
        risk_notes = match.policy.get("risk_notes", [])
        if isinstance(risk_notes, list) and risk_notes:
            notes.append(f"{match.policy_id}：{risk_notes[0]}")
    return notes


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """判断文本是否命中任意关键词。

    Args:
        text: 待匹配文本。
        keywords: 关键词元组。

    Returns:
        命中时返回 True。
    """

    normalized = text.casefold()
    return any(keyword.casefold() in normalized for keyword in keywords)


def _deduplicate(values: list[str]) -> list[str]:
    """按顺序去重。

    Args:
        values: 待去重列表。

    Returns:
        去重后的列表。
    """

    result = []
    seen = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
