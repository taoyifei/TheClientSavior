"""客户拯救者轻量智能体编排。"""

from __future__ import annotations

import re
import time
from typing import Any

from src.llm_client import generate_with_llm
from src.llm_client import get_llm_settings
from src.llm_client import is_llm_configured
from src.matcher import match_policies
from src.models import AgentResult
from src.models import CustomerProfile
from src.models import PolicyMatch
from src.templates import build_fallback_result


class ClientSaviorAgent:
    """串联本地召回、LLM 生成和模板兜底。"""

    def __init__(self, policies: list[dict[str, object]]):
        """初始化智能体。

        Args:
            policies: 本地政策库。

        Returns:
            无返回值。
        """

        self.policies = policies

    def run(
        self,
        complaint: str,
        profile: CustomerProfile,
        use_llm: bool = True,
    ) -> AgentResult:
        """运行一次投诉挽留方案生成。

        Args:
            complaint: 客户投诉原文。
            profile: 客户画像。
            use_llm: 是否启用 LLM 链路。

        Returns:
            统一智能体输出。
        """

        started_at = time.perf_counter()
        local_matches = match_policies(
            complaint=complaint,
            profile=profile,
            policies=self.policies,
            top_k=5,
        )
        profile_dict = profile.to_dict()
        candidate_policies = [match.policy for match in local_matches]
        settings = get_llm_settings()
        model = str(settings["model"])

        llm_error = None
        if use_llm:
            if is_llm_configured():
                try:
                    llm_payload = generate_with_llm(
                        complaint=complaint,
                        profile=profile_dict,
                        candidate_policies=candidate_policies,
                    )
                    llm_result = _ensure_result_dict(llm_payload.get("result"))
                    merged_result = self._merge_result(llm_result, local_matches)
                    return AgentResult(
                        mode="llm",
                        model=str(llm_payload.get("model", model)),
                        elapsed_seconds=float(
                            llm_payload.get("elapsed_seconds", 0.0)
                        ),
                        cached=bool(llm_payload.get("cached", False)),
                        customer_analysis=merged_result["customer_analysis"],
                        recommended_policies=merged_result["recommended_policies"],
                        retention_script=merged_result["retention_script"],
                        internal_notes=merged_result["internal_notes"],
                        local_matches=[match.to_dict() for match in local_matches],
                        llm_error=None,
                    )
                except Exception as exc:
                    llm_error = _summarize_error(exc)
            else:
                llm_error = "未配置有效的 LLM API Key，已切换本地模板兜底。"

        fallback_result = build_fallback_result(
            complaint=complaint,
            profile=profile_dict,
            matches=local_matches,
        )
        merged_fallback = self._merge_result(fallback_result, local_matches)
        if llm_error:
            merged_fallback["internal_notes"].insert(
                0,
                f"LLM调用失败，已切换本地兜底：{llm_error}",
            )
        return AgentResult(
            mode="fallback",
            model=model,
            elapsed_seconds=time.perf_counter() - started_at,
            cached=False,
            customer_analysis=merged_fallback["customer_analysis"],
            recommended_policies=merged_fallback["recommended_policies"],
            retention_script=merged_fallback["retention_script"],
            internal_notes=merged_fallback["internal_notes"],
            local_matches=[match.to_dict() for match in local_matches],
            llm_error=llm_error,
        )

    def _merge_result(
        self,
        result: dict[str, object],
        local_matches: list[PolicyMatch],
    ) -> dict[str, Any]:
        """把 LLM 或模板结果与本地政策详情合并。

        Args:
            result: LLM 或模板输出。
            local_matches: 本地召回政策列表。

        Returns:
            补齐本地分数、原因和政策卡详情后的结果。
        """

        local_by_id = {match.policy_id: match for match in local_matches}
        recommended = _normalize_recommendations(
            result.get("recommended_policies"),
            local_matches,
            local_by_id,
        )
        return {
            "customer_analysis": _normalize_analysis(
                result.get("customer_analysis")
            ),
            "recommended_policies": recommended,
            "retention_script": _normalize_script(
                result.get("retention_script")
            ),
            "internal_notes": _normalize_notes(result.get("internal_notes")),
        }


def _ensure_result_dict(value: object) -> dict[str, object]:
    """确保 LLM 输出为字典。

    Args:
        value: 待校验对象。

    Returns:
        通过校验的字典。

    Raises:
        ValueError: 对象不是字典时抛出。
    """

    if not isinstance(value, dict):
        raise ValueError("LLM 输出必须是字典。")
    return value


def _normalize_analysis(value: object) -> dict[str, object]:
    """规范化客户分析结构。

    Args:
        value: 原始客户分析对象。

    Returns:
        补齐字段后的客户分析结构。
    """

    analysis = value if isinstance(value, dict) else {}
    return {
        "complaint_type": str(analysis.get("complaint_type", "其他")),
        "emotion": str(analysis.get("emotion", "不满")),
        "risk_level": str(analysis.get("risk_level", "中")),
        "key_needs": _ensure_list(analysis.get("key_needs")),
        "summary": str(analysis.get("summary", "客户需要可核验的解决方案。")),
    }


def _normalize_script(value: object) -> dict[str, str]:
    """规范化四段式话术。

    Args:
        value: 原始话术对象。

    Returns:
        补齐字段后的四段式话术。
    """

    script = value if isinstance(value, dict) else {}
    return {
        "opening": str(script.get("opening", "您好，我先帮您看一下当前问题。")),
        "solution": str(script.get("solution", "我会结合您的套餐和政策资格给出方案。")),
        "risk_disclosure": str(
            script.get("risk_disclosure", "办理前需以系统办理结果为准。")
        ),
        "next_step": str(script.get("next_step", "接下来可以先核查可办理资格。")),
    }


def _normalize_notes(value: object) -> list[str]:
    """规范化内部提醒。

    Args:
        value: 原始内部提醒对象。

    Returns:
        内部提醒列表。
    """

    notes = _ensure_list(value)
    if not notes:
        return ["办理前请核查客户标签、合约互斥和系统可办理资格。"]
    return [str(note) for note in notes]


def _normalize_recommendations(
    value: object,
    local_matches: list[PolicyMatch],
    local_by_id: dict[str, PolicyMatch],
) -> list[dict[str, object]]:
    """规范化推荐政策并补齐本地信息。

    Args:
        value: LLM 或模板推荐列表。
        local_matches: 本地召回列表。
        local_by_id: 本地召回索引。

    Returns:
        页面可渲染的 Top 3 推荐政策。
    """

    raw_recommendations = value if isinstance(value, list) else []
    merged = []
    used_ids = set()
    for raw_item in raw_recommendations:
        if not isinstance(raw_item, dict):
            continue
        policy_id = str(raw_item.get("policy_id", ""))
        match = local_by_id.get(policy_id)
        if match is None or policy_id in used_ids:
            continue
        merged.append(_build_policy_view(raw_item, match, len(merged) + 1))
        used_ids.add(policy_id)
        if len(merged) >= 3:
            break

    for match in local_matches:
        if len(merged) >= 3:
            break
        if match.policy_id in used_ids:
            continue
        merged.append(_build_policy_view({}, match, len(merged) + 1))
        used_ids.add(match.policy_id)
    return merged


def _build_policy_view(
    raw_item: dict[str, object],
    match: PolicyMatch,
    rank: int,
) -> dict[str, object]:
    """构建推荐政策的页面视图。

    Args:
        raw_item: LLM 或模板中的推荐项。
        match: 本地政策候选。
        rank: 推荐排序。

    Returns:
        推荐政策视图字典。
    """

    return {
        "policy_id": match.policy_id,
        "rank": _safe_rank(raw_item.get("rank", rank), rank),
        "title": match.title,
        "reason": str(
            raw_item.get(
                "reason",
                match.reasons[0] if match.reasons else "本地匹配度较高。",
            )
        ),
        "talking_point": str(
            raw_item.get(
                "talking_point",
                match.policy.get("script_hint", "适合当前客户诉求。"),
            )
        ),
        "local_score": match.score,
        "local_reasons": match.reasons,
        "policy": match.policy,
    }


def _ensure_list(value: object) -> list[object]:
    """把任意对象规范为列表。

    Args:
        value: 待规范对象。

    Returns:
        列表形式的值。
    """

    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _summarize_error(exc: Exception) -> str:
    """生成不暴露敏感信息的错误摘要。

    Args:
        exc: 原始异常。

    Returns:
        最多 120 字的错误摘要。
    """

    message = str(exc) or exc.__class__.__name__
    redacted = _redact_secret(message)
    if len(redacted) <= 120:
        return redacted
    return redacted[:117].rstrip() + "..."


def _safe_rank(value: object, default: int) -> int:
    """把 LLM 返回的排序值安全转换为 1 到 3 的整数。

    Args:
        value: 原始排序值。
        default: 解析失败时使用的默认排序。

    Returns:
        规范化后的排序值。
    """

    rank = _parse_rank(value)
    if rank is None:
        rank = default
    return max(1, min(3, int(rank)))


def _parse_rank(value: object) -> int | None:
    """解析排序值。

    Args:
        value: 原始排序值。

    Returns:
        解析成功返回整数，否则返回 None。
    """

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)

    number_match = re.search(r"\d+", text)
    if number_match:
        return int(number_match.group(0))

    chinese_rank_map = {"一": 1, "二": 2, "三": 3}
    for chinese_number, rank in chinese_rank_map.items():
        if chinese_number in text:
            return rank
    return None


def _redact_secret(message: str) -> str:
    """脱敏可能出现在异常中的 Key 信息。

    Args:
        message: 原始错误消息。

    Returns:
        脱敏后的错误消息。
    """

    patterns = (
        (r"sk-\S+", "sk-***"),
        (r"Bearer\s+\S+", "Bearer ***"),
        (r"DASHSCOPE_API_KEY=\S+", "DASHSCOPE_API_KEY=***"),
        (r"OPENAI_API_KEY=\S+", "OPENAI_API_KEY=***"),
    )
    redacted = message
    for pattern, replacement in patterns:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)
    return redacted
