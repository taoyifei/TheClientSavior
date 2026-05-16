"""FastAPI 接口冒烟测试，需要先启动后端服务。"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    """验证主要 API 可以被前端调用。"""

    health = _get_json("/api/health")
    _assert(health["status"] == "ok", "健康检查失败。")

    policies = _get_json("/api/policies")
    _assert(len(policies) >= 12, "政策库接口返回不足 12 条。")

    demo_cases = _get_json("/api/demo-cases")
    _assert(len(demo_cases) >= 6, "演示案例接口返回不足 6 条。")
    _assert(
        all(bool(case.get("phone")) for case in demo_cases),
        "演示案例必须全部包含 phone 字段。",
    )

    lookup = _get_json("/api/customers/lookup?phone=13800138001")
    _assert(lookup["found"] is True, "客户查询应命中演示客户。")
    _assert("phone" not in lookup["customer"], "客户查询不能返回完整手机号字段。")
    _assert(
        lookup["customer"]["phone_masked"] == "138****8001",
        "客户查询只能返回脱敏手机号。",
    )

    generate_payload = {
        "phone": "13800138001",
        "complaint": demo_cases[0]["complaint"],
        "profile": demo_cases[0]["profile"],
        "use_llm": False,
    }
    generated = _post_json("/api/generate", generate_payload)
    _assert(generated["mode"] == "fallback", "关闭 LLM 时必须返回本地模板兜底。")
    _assert(
        "13800138001" not in json.dumps(generated, ensure_ascii=False),
        "生成接口不能返回完整手机号。",
    )
    first_policy = generated["recommended_policies"][0]
    _assert(first_policy.get("title"), "推荐政策必须包含 title。")
    _assert(first_policy.get("reason"), "推荐政策必须包含 reason。")
    _assert(
        first_policy.get("policy")
        or first_policy.get("category")
        or first_policy.get("price")
        or first_policy.get("benefits"),
        "推荐政策必须包含 policy 或拍平后的展示字段。",
    )

    dashboard = _get_json("/api/dashboard")
    _assert(
        dashboard["metrics"]["total_cases"] >= 1,
        "生成后看板记录数必须增加。",
    )
    first_record = dashboard["risk_queue"][0]
    for key in ("phone_masked", "risk_level", "top_business", "complaint_type"):
        _assert(key in first_record, f"看板记录缺少英文字段：{key}。")

    csv_text = _get_bytes("/api/dashboard/export").decode("utf-8-sig")
    _assert("138****8001" in csv_text, "CSV 必须包含脱敏手机号。")
    _assert("13800138001" not in csv_text, "CSV 不能包含完整手机号。")

    print("api_smoke_test_ok")


def _get_json(path: str) -> object:
    """发送 GET 请求并解析 JSON。"""

    return json.loads(_get_bytes(path).decode("utf-8"))


def _get_bytes(path: str) -> bytes:
    """发送 GET 请求并返回原始字节。"""

    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=10) as response:
        return response.read()


def _post_json(path: str, payload: dict[str, object]) -> object:
    """发送 POST JSON 请求并解析 JSON。"""

    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(f"接口请求失败：{exc.code} {detail}") from exc


def _assert(condition: bool, message: str) -> None:
    """抛出中文断言错误。"""

    if not condition:
        raise AssertionError(message)


if __name__ == "__main__":
    main()
