"""本地客户查询与手机号隐私处理。"""

from __future__ import annotations

from backend.services.data_service import load_customers


def normalize_phone(raw: object) -> str:
    """标准化手机号。

    Args:
        raw: 原始手机号输入。

    Returns:
        去除空格和短横线后的手机号。
    """

    if raw is None:
        return ""
    return str(raw).replace(" ", "").replace("-", "").strip()


def mask_phone(phone: str) -> str:
    """脱敏手机号。

    Args:
        phone: 标准化手机号。

    Returns:
        脱敏后的手机号展示文本。
    """

    if not phone:
        return "未填写"
    if phone.isdigit() and len(phone) == 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return f"{phone[:3]}****"


def find_customer_by_phone(phone: str) -> dict[str, object] | None:
    """按手机号查找本地演示客户。

    Args:
        phone: 标准化手机号。

    Returns:
        命中的客户画像；未命中时返回 None。
    """

    for customer in load_customers():
        if normalize_phone(customer.get("phone")) == phone:
            return dict(customer)
    return None


def public_customer_view(customer: dict[str, object]) -> dict[str, object]:
    """生成前端可见的客户视图，不包含完整手机号。

    Args:
        customer: 原始本地客户画像。

    Returns:
        脱敏后的客户视图。
    """

    public_view = dict(customer)
    public_view.pop("phone", None)
    public_view["phone_masked"] = mask_phone(normalize_phone(customer.get("phone")))
    return public_view


def apply_customer_to_profile(customer: dict[str, object]) -> dict[str, object]:
    """把本地客户画像转换为生成接口画像。

    Args:
        customer: 原始本地客户画像。

    Returns:
        不含手机号的客户画像字典。
    """

    return {
        "monthly_fee": int(customer.get("monthly_fee", 39)),
        "customer_type": str(customer.get("customer_type", "存量")),
        "tenure_years": float(customer.get("tenure_years", 0)),
        "has_broadband": bool(customer.get("has_broadband", False)),
        "wants_device": bool(customer.get("wants_device", False)),
        "family_mobile_count": int(customer.get("family_mobile_count", 1)),
        "wants_port_out": bool(customer.get("wants_port_out", False)),
    }
