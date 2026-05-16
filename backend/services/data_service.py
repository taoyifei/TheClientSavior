"""本地 JSON 数据读取服务。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from src.matcher import load_policies as read_policies

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


@lru_cache(maxsize=1)
def load_policies() -> list[dict[str, object]]:
    """加载政策库。

    Args:
        无参数。

    Returns:
        政策卡列表。
    """

    return read_policies(DATA_DIR / "policies.json")


@lru_cache(maxsize=1)
def load_demo_cases() -> list[dict[str, object]]:
    """加载演示案例。

    Args:
        无参数。

    Returns:
        演示案例列表。
    """

    return _load_json_list(DATA_DIR / "demo_cases.json")


@lru_cache(maxsize=1)
def load_customers() -> list[dict[str, object]]:
    """加载本地演示客户画像。

    Args:
        无参数。

    Returns:
        客户画像列表，文件不存在时返回空列表。
    """

    customers_path = DATA_DIR / "customers.json"
    if not customers_path.exists():
        return []
    return _load_json_list(customers_path)


def _load_json_list(path: Path) -> list[dict[str, object]]:
    """读取 JSON 数组文件。

    Args:
        path: JSON 文件路径。

    Returns:
        JSON 对象列表。

    Raises:
        ValueError: 文件内容不是 JSON 数组时抛出。
    """

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 必须是 JSON 数组。")
    return data
