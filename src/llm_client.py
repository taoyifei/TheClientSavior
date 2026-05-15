"""OpenAI-compatible LLM 调用与 JSON 解析。"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 依赖缺失时仍允许本地兜底。
    load_dotenv = None

COMPACT_POLICY_FIELDS = (
    "id",
    "title",
    "category",
    "price",
    "target",
    "benefits",
    "conditions",
    "risk_notes",
    "script_hint",
)
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-flash"
DEFAULT_TIMEOUT = 6.0
DEFAULT_MAX_TOKENS = 800
DEFAULT_TEMPERATURE = 0.2
SYSTEM_PROMPT = """你是中国移动一线投诉挽留专家，也是一个严谨的 AI 助手。
你的任务是根据客户投诉、客户画像和候选政策，生成可执行的挽留方案。
要求：
1. 只能从候选政策 id 中选择，不能编造政策或产品；
2. recommended_policies 最多返回 3 个；
3. 涉及办理资格、合约、优惠期、预存、初装费、调测费时，必须提示“以系统办理结果为准”；
4. 话术要像一线客服，先安抚，再解释，再引导办理；
5. 输出必须是合法 JSON，不要 Markdown，不要多余解释。"""

_CACHE: dict[str, dict[str, Any]] = {}
_ENV_LOADED = False


def is_llm_configured() -> bool:
    """判断是否已配置可用的 LLM API Key。

    Args:
        无参数。

    Returns:
        已配置 API Key 时返回 True。
    """

    settings = get_llm_settings()
    return not _is_placeholder_api_key(settings["api_key"])


def get_llm_settings() -> dict[str, object]:
    """读取 LLM 环境配置。

    Args:
        无参数。

    Returns:
        包含 API Key、Base URL、模型、超时和输出长度的字典。
    """

    _load_env_once()
    return {
        "api_key": os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL", DEFAULT_BASE_URL),
        "model": os.getenv("LLM_MODEL", DEFAULT_MODEL),
        "timeout": _read_float_env("LLM_TIMEOUT", DEFAULT_TIMEOUT),
        "max_tokens": _read_int_env("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS),
    }


def compact_policy(policy: dict[str, object]) -> dict[str, object]:
    """压缩政策卡，避免把完整对象发送给 LLM。

    Args:
        policy: 原始政策卡。

    Returns:
        只包含必要字段的精简政策卡。
    """

    compacted: dict[str, object] = {}
    for field_name in COMPACT_POLICY_FIELDS:
        value = policy.get(field_name, "")
        if isinstance(value, list):
            compacted[field_name] = [_truncate_text(item) for item in value[:4]]
        else:
            compacted[field_name] = _truncate_text(value)
    return compacted


def generate_with_llm(
    complaint: str,
    profile: dict[str, object],
    candidate_policies: list[dict[str, object]],
) -> dict[str, object]:
    """调用 LLM 生成结构化挽留方案。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        candidate_policies: 本地召回的候选政策。

    Returns:
        包含 LLM 结果、耗时、模型和缓存标记的字典。

    Raises:
        RuntimeError: LLM 未配置或 SDK 不可用。
        ValueError: LLM 返回内容为空或无法解析为 JSON。
        Exception: OpenAI-compatible SDK 调用中的网络或超时异常。
    """

    settings = get_llm_settings()
    if _is_placeholder_api_key(settings["api_key"]):
        raise RuntimeError("未配置有效的 LLM API Key。")

    compact_policies = [compact_policy(policy) for policy in candidate_policies]
    cache_key = _make_cache_key(complaint, profile, compact_policies)
    if cache_key in _CACHE:
        cached_payload = copy.deepcopy(_CACHE[cache_key])
        cached_payload["cached"] = True
        cached_payload["elapsed_seconds"] = 0.0
        return cached_payload

    client = _build_openai_client(settings)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_prompt(complaint, profile, compact_policies),
        },
    ]

    started_at = time.perf_counter()
    response = _create_completion(
        client=client,
        settings=settings,
        messages=messages,
        use_response_format=True,
    )
    elapsed_seconds = time.perf_counter() - started_at
    content = _extract_content(response)
    result = _parse_json_content(content)

    payload = {
        "result": result,
        "elapsed_seconds": elapsed_seconds,
        "model": settings["model"],
        "cached": False,
    }
    _CACHE[cache_key] = copy.deepcopy(payload)
    return payload


def test_llm_connection() -> dict[str, object]:
    """用极短请求测试 LLM 连通性。

    Args:
        无参数。

    Returns:
        连通性测试结果字典。

    Raises:
        RuntimeError: 未配置 API Key 或 SDK 不可用。
        Exception: 网络、鉴权或兼容接口异常。
    """

    settings = get_llm_settings()
    if _is_placeholder_api_key(settings["api_key"]):
        raise RuntimeError("未配置有效的 LLM API Key。")

    client = _build_openai_client(settings)
    messages = [
        {"role": "system", "content": "你只返回合法 JSON。"},
        {"role": "user", "content": "返回 {\"ok\": true}"},
    ]
    started_at = time.perf_counter()
    response = _create_completion(
        client=client,
        settings={**settings, "max_tokens": 32},
        messages=messages,
        use_response_format=True,
    )
    elapsed_seconds = time.perf_counter() - started_at
    _parse_json_content(_extract_content(response))
    return {
        "ok": True,
        "elapsed_seconds": elapsed_seconds,
        "model": settings["model"],
    }


def _create_completion(
    client: object,
    settings: dict[str, object],
    messages: list[dict[str, str]],
    use_response_format: bool,
) -> object:
    """创建聊天补全，必要时兼容不支持 JSON 模式的接口。

    Args:
        client: OpenAI SDK 客户端。
        settings: LLM 配置字典。
        messages: 消息列表。
        use_response_format: 是否尝试 JSON response_format。

    Returns:
        OpenAI SDK 响应对象。

    Raises:
        Exception: 网络、鉴权、超时或非兼容参数之外的异常。
    """

    kwargs = {
        "model": str(settings["model"]),
        "messages": messages,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": int(settings["max_tokens"]),
    }
    if not use_response_format:
        return client.chat.completions.create(**kwargs)

    try:
        return client.chat.completions.create(
            **kwargs,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        if _is_response_format_error(exc):
            return client.chat.completions.create(**kwargs)
        raise


def _load_env_once() -> None:
    """按需加载 .env 文件。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    global _ENV_LOADED
    if _ENV_LOADED:
        return
    if load_dotenv is not None:
        load_dotenv(encoding="utf-8-sig")
    _ENV_LOADED = True


def _is_placeholder_api_key(value: object) -> bool:
    """判断 API Key 是否为空或明显占位符。

    Args:
        value: 待判断的 API Key 值。

    Returns:
        为空或占位符时返回 True。
    """

    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    lowered = text.casefold()
    placeholder_markers = (
        "替换",
        "your-api-key",
        "your_api_key",
        "xxx",
        "example",
        "demo",
        "test",
        "请填写",
    )
    if any(marker.casefold() in lowered for marker in placeholder_markers):
        return True
    return len(text) < 12


def _build_openai_client(settings: dict[str, object]) -> object:
    """创建 OpenAI-compatible 客户端。

    Args:
        settings: LLM 配置字典。

    Returns:
        OpenAI SDK 客户端实例。

    Raises:
        RuntimeError: OpenAI SDK 未安装时抛出。
    """

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI SDK 未安装。") from exc

    return OpenAI(
        api_key=str(settings["api_key"]),
        base_url=str(settings["base_url"]),
        timeout=float(settings["timeout"]),
    )


def _build_user_prompt(
    complaint: str,
    profile: dict[str, object],
    candidate_policies: list[dict[str, object]],
) -> str:
    """构建用户提示词。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        candidate_policies: 精简候选政策。

    Returns:
        发送给 LLM 的用户提示词。
    """

    profile_json = json.dumps(profile, ensure_ascii=False, sort_keys=True)
    policies_json = json.dumps(candidate_policies, ensure_ascii=False)
    candidate_ids = [str(policy.get("id", "")) for policy in candidate_policies]
    return f"""客户投诉：
{complaint}

客户画像：
{profile_json}

候选政策 Top 5：
{policies_json}

候选政策 id 只能从这个列表中选择：
{candidate_ids}

请输出如下 JSON。recommended_policies 最多 3 个，且 policy_id 必须来自候选政策 id：
{{
  "customer_analysis": {{
    "complaint_type": "流量不足/资费争议/宽带质量/换机需求/家庭融合/商客需求/离网风险/其他",
    "emotion": "平稳/不满/强烈不满",
    "risk_level": "低/中/高",
    "key_needs": ["..."],
    "summary": "..."
  }},
  "recommended_policies": [
    {{
      "policy_id": "Pxx",
      "rank": 1,
      "reason": "为什么推荐该政策",
      "talking_point": "面向客户的一句话卖点"
    }}
  ],
  "retention_script": {{
    "opening": "安抚开场，不超过80字",
    "solution": "结合推荐政策说明解决方案，不超过180字",
    "risk_disclosure": "必须提醒办理资格、合约、优惠期、预存、初装费、调测费以系统办理结果为准，不超过120字",
    "next_step": "下一步引导，不超过80字"
  }},
  "internal_notes": ["给一线人员看的办理提醒"]
}}"""


def _make_cache_key(
    complaint: str,
    profile: dict[str, object],
    candidate_policies: list[dict[str, object]],
) -> str:
    """生成 LLM 缓存 Key。

    Args:
        complaint: 客户投诉原文。
        profile: 客户画像字典。
        candidate_policies: 精简候选政策。

    Returns:
        MD5 哈希字符串。
    """

    candidate_ids = ",".join(
        str(policy.get("id", "")) for policy in candidate_policies
    )
    raw_key = (
        complaint
        + json.dumps(profile, ensure_ascii=False, sort_keys=True)
        + candidate_ids
    )
    return hashlib.md5(raw_key.encode("utf-8")).hexdigest()


def _extract_content(response: object) -> str:
    """从 SDK 响应中提取模型文本。

    Args:
        response: OpenAI SDK 响应对象。

    Returns:
        模型返回文本。

    Raises:
        ValueError: 响应内容为空时抛出。
    """

    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("LLM 响应缺少 choices。")
    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if not content:
        raise ValueError("LLM 响应内容为空。")
    return str(content)


def _parse_json_content(content: str) -> dict[str, object]:
    """稳健解析 LLM 返回的 JSON。

    Args:
        content: LLM 原始返回文本。

    Returns:
        解析后的 JSON 字典。

    Raises:
        ValueError: 返回内容无法解析为 JSON 对象时抛出。
    """

    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM 响应中未找到 JSON 对象。")

    parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM 响应 JSON 顶层必须是对象。")
    return parsed


def _read_float_env(name: str, default: float) -> float:
    """读取浮点型环境变量。

    Args:
        name: 环境变量名。
        default: 默认值。

    Returns:
        解析后的浮点数。
    """

    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _read_int_env(name: str, default: int) -> int:
    """读取整型环境变量。

    Args:
        name: 环境变量名。
        default: 默认值。

    Returns:
        解析后的整数。
    """

    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _truncate_text(value: object, limit: int = 160) -> str:
    """截断长文本字段。

    Args:
        value: 原始字段值。
        limit: 最大字符数。

    Returns:
        截断后的文本。
    """

    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _is_response_format_error(exc: Exception) -> bool:
    """判断异常是否来自 response_format 兼容性问题。

    Args:
        exc: SDK 调用异常。

    Returns:
        属于 JSON 模式兼容性问题时返回 True。
    """

    message = str(exc).casefold()
    keywords = (
        "response_format",
        "json_object",
        "unsupported",
        "not support",
        "invalid parameter",
        "unknown parameter",
    )
    return any(keyword in message for keyword in keywords)
