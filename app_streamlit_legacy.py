"""Legacy Streamlit 入口；新版主界面请使用 backend/ + frontend/。"""

from __future__ import annotations

import csv
import html
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from src.agent import ClientSaviorAgent
from src.llm_client import get_llm_settings
from src.llm_client import is_llm_configured
from src.llm_client import test_llm_connection
from src.matcher import load_policies as read_policies
from src.models import AgentResult
from src.models import CustomerProfile

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CUSTOMER_TYPES = ["新入网", "存量", "高套", "家庭用户", "商客"]
SCRIPT_SECTIONS = (
    ("opening", "安抚开场"),
    ("solution", "方案介绍"),
    ("risk_disclosure", "风险说明"),
    ("next_step", "下一步引导"),
)
HISTORY_VISIBLE_COLUMNS = [
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


def main() -> None:
    """渲染 Streamlit 页面。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.set_page_config(
        page_title="The Client Savior｜客户拯救者",
        page_icon="CS",
        layout="wide",
    )
    _inject_css()
    _initialize_session_state()
    _stop_if_policy_file_missing()
    policies = load_policies()
    demo_cases = load_demo_cases()
    customers = load_customers()
    settings = get_llm_settings()

    _render_sidebar(settings)
    _render_app_shell_header(settings)
    selected_page = _render_top_navigation()

    if selected_page == "workbench":
        _render_workbench_page(policies, demo_cases, customers)
    elif selected_page == "dashboard":
        _render_dashboard_page()
    else:
        _render_policy_library_page(policies)


@st.cache_data(show_spinner=False)
def load_policies() -> list[dict[str, object]]:
    """加载并缓存政策库。

    Args:
        无参数。

    Returns:
        政策卡列表。
    """

    return read_policies(DATA_DIR / "policies.json")


@st.cache_data(show_spinner=False)
def load_demo_cases() -> list[dict[str, object]]:
    """加载并缓存演示案例。

    Args:
        无参数。

    Returns:
        演示案例列表。
    """

    cases_path = DATA_DIR / "demo_cases.json"
    if not cases_path.exists():
        return []

    with cases_path.open("r", encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError("演示案例必须是 JSON 数组。")
    return cases


@st.cache_data(show_spinner=False)
def load_customers() -> list[dict[str, object]]:
    """加载本地演示客户画像。

    Args:
        无参数。

    Returns:
        客户画像列表。
    """

    customers_path = DATA_DIR / "customers.json"
    if not customers_path.exists():
        return []
    with customers_path.open("r", encoding="utf-8") as file:
        customers = json.load(file)
    if not isinstance(customers, list):
        raise ValueError("客户画像必须是 JSON 数组。")
    return customers


def _inject_css() -> None:
    """注入页面级 CSS，提升现场演示观感。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.markdown(
        """
        <style>
        :root {
            --brand: #1677ff;
            --brand-700: #0b5ed7;
            --navy: #0b2f6b;
            --surface: #ffffff;
            --bg: #f5f8fc;
            --risk-red: #d92d20;
            --risk-red-bg: #fff1f0;
            --warn: #f79009;
            --warn-bg: #fff7e6;
            --success: #12b76a;
            --success-bg: #ecfdf3;
            --radius-lg: 24px;
            --radius-md: 16px;
            --shadow-sm: 0 4px 14px rgba(16, 24, 40, 0.06);
            --shadow-md: 0 12px 32px rgba(16, 24, 40, 0.10);
            --mobile-blue: #1677ff;
            --deep-blue: #0b2f6b;
            --ink: #101828;
            --muted: #667085;
            --line: rgba(16, 24, 40, 0.10);
            --card: rgba(255, 255, 255, 0.96);
            --soft-blue: #eef6ff;
            --soft-green: #ebf9f1;
            --soft-orange: #fff6e8;
            --soft-red: #fff0f0;
        }

        .stApp,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            color: var(--ink) !important;
            background:
                linear-gradient(180deg, #f4f9ff 0%, #ffffff 42%, #f7fbff 100%)
                !important;
        }

        [data-testid="stHeader"] {
            background: rgba(244, 249, 255, 0.94) !important;
            backdrop-filter: blur(8px);
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"] {
            color: var(--ink) !important;
            background: #f7fbff !important;
        }

        .stMarkdown,
        .stMarkdown p,
        .stCaption,
        label,
        [data-testid="stWidgetLabel"],
        [data-testid="stMarkdownContainer"] {
            color: var(--ink);
        }

        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] label {
            color: var(--ink);
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] button {
            color: var(--ink) !important;
            background: #ffffff !important;
            border: 1px solid rgba(16, 32, 51, 0.18) !important;
            border-radius: 10px !important;
        }

        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            color: var(--deep-blue) !important;
            border-color: rgba(22, 119, 255, 0.45) !important;
            background: #f4f9ff !important;
        }

        textarea,
        input,
        [data-baseweb="input"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="select"] > div {
            color: var(--ink) !important;
            background: #ffffff !important;
            border-color: rgba(16, 32, 51, 0.16) !important;
        }

        [data-baseweb="tab-list"] {
            border-bottom: 1px solid rgba(16, 32, 51, 0.12);
        }

        button[data-baseweb="tab"] {
            color: #344054 !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--mobile-blue) !important;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero-card {
            padding: 28px 32px;
            border-radius: 22px;
            background:
                linear-gradient(135deg, rgba(22, 119, 255, 0.13), transparent 42%),
                linear-gradient(120deg, #ffffff 0%, #f7fbff 100%);
            border: 1px solid var(--line);
            box-shadow: 0 14px 35px rgba(16, 32, 51, 0.08);
            margin-bottom: 18px;
        }

        .hero-title {
            font-size: 2.4rem;
            line-height: 1.15;
            font-weight: 800;
            color: var(--deep-blue);
            margin-bottom: 10px;
            letter-spacing: 0;
        }

        .hero-subtitle {
            font-size: 1.05rem;
            color: var(--muted);
            margin-bottom: 16px;
        }

        .section-title {
            font-size: 1.15rem;
            font-weight: 760;
            color: var(--ink);
            margin: 8px 0 14px;
        }

        .step-card, .policy-card, .script-card, .note-card,
        .copy-box, .summary-card, .analysis-card, .empty-card,
        .flow-card, .library-card {
            border: 1px solid rgba(16, 32, 51, 0.10);
            border-radius: 16px;
            background: var(--card);
            box-shadow: 0 10px 28px rgba(16, 32, 51, 0.06);
        }

        .step-card {
            min-height: 128px;
            padding: 18px;
        }

        .step-card b {
            display: block;
            color: var(--deep-blue);
            font-size: 1rem;
            margin-bottom: 8px;
        }

        .step-card span {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.62;
        }

        .summary-card {
            min-height: 112px;
            padding: 16px 18px;
            margin-bottom: 10px;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin: 10px 0 12px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.84rem;
            margin-bottom: 8px;
        }

        .metric-value {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 780;
            line-height: 1.25;
        }

        .status-pill, .chip, .policy-rank {
            display: inline-flex;
            align-items: center;
            width: fit-content;
            border-radius: 999px;
            font-weight: 720;
            white-space: nowrap;
        }

        .status-pill {
            padding: 6px 10px;
            font-size: 0.86rem;
        }

        .status-llm {
            color: #087443;
            background: var(--soft-green);
            border: 1px solid rgba(8, 116, 67, 0.18);
        }

        .status-fallback {
            color: #b15c00;
            background: var(--soft-orange);
            border: 1px solid rgba(177, 92, 0, 0.18);
        }

        .risk-high {
            color: #c21d1d;
            background: var(--soft-red);
            border: 1px solid rgba(194, 29, 29, 0.18);
        }

        .risk-medium {
            color: #b15c00;
            background: var(--soft-orange);
            border: 1px solid rgba(177, 92, 0, 0.18);
        }

        .risk-low {
            color: #087443;
            background: var(--soft-green);
            border: 1px solid rgba(8, 116, 67, 0.18);
        }

        .policy-card, .analysis-card, .script-card,
        .note-card, .copy-box, .flow-card, .library-card {
            padding: 18px;
            margin: 12px 0;
        }

        .policy-rank {
            color: #ffffff;
            background: linear-gradient(135deg, #1677ff, #0b2f6b);
            padding: 5px 10px;
            font-size: 0.8rem;
            margin-bottom: 10px;
        }

        .policy-title {
            color: var(--ink);
            font-size: 1.18rem;
            font-weight: 780;
            margin: 4px 0 8px;
        }

        .policy-meta {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.6;
        }

        .chip {
            color: #1250a5;
            background: var(--soft-blue);
            border: 1px solid rgba(22, 119, 255, 0.15);
            padding: 5px 9px;
            margin: 3px 5px 3px 0;
            font-size: 0.82rem;
        }

        .script-card {
            min-height: 150px;
            border-left: 5px solid var(--mobile-blue);
        }

        .script-card b {
            display: block;
            color: var(--deep-blue);
            margin-bottom: 8px;
        }

        .script-card span, .note-card span,
        .analysis-card p, .library-card p {
            color: #344054;
            line-height: 1.65;
        }

        .note-card {
            background: #f4f9ff;
        }

        .copy-box {
            background: #f8fbff;
        }

        .empty-card {
            padding: 42px 28px;
            min-height: 380px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
            color: var(--muted);
        }

        .empty-card b {
            color: var(--deep-blue);
            font-size: 1.25rem;
            margin-bottom: 10px;
        }

        .warning-strip {
            background: #fff7e6;
            color: #9a5b00;
            border: 1px solid rgba(154, 91, 0, 0.18);
            border-radius: 14px;
            padding: 12px 14px;
            margin: 10px 0 12px;
        }

        .flow-card {
            color: var(--deep-blue);
            font-weight: 780;
            text-align: center;
            background: linear-gradient(90deg, #f2f8ff, #ffffff);
        }

        .field-label-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin: 8px 0 6px;
        }

        .field-label-row span {
            color: var(--ink);
            font-weight: 700;
        }

        .voice-button {
            color: #8a5a00;
            background: #fff7e6;
            border: 1px solid rgba(177, 92, 0, 0.24);
            border-radius: 999px;
            padding: 5px 11px;
            font-size: 0.84rem;
            font-weight: 720;
            cursor: help;
        }

        .voice-tooltip {
            position: relative;
            display: inline-flex;
            align-items: center;
        }

        .voice-tooltip-text {
            visibility: hidden;
            opacity: 0;
            position: absolute;
            right: 0;
            bottom: calc(100% + 8px);
            z-index: 10;
            min-width: 132px;
            color: #ffffff;
            background: rgba(16, 32, 51, 0.92);
            border-radius: 8px;
            padding: 7px 10px;
            font-size: 0.82rem;
            text-align: center;
            transition: opacity 0.15s ease;
            pointer-events: none;
        }

        .voice-tooltip:hover .voice-tooltip-text {
            visibility: visible;
            opacity: 1;
        }

        .library-card {
            border-left: 5px solid var(--mobile-blue);
        }

        .risk-client-card {
            padding: 16px;
            margin: 8px 0;
            border: 1px solid rgba(194, 29, 29, 0.18);
            border-left: 5px solid #d92d20;
            border-radius: 16px;
            background: #fffafa;
            box-shadow: 0 8px 20px rgba(16, 32, 51, 0.05);
        }

        .risk-client-card b {
            color: #b42318;
            font-size: 1rem;
        }

        .lookup-panel, .customer-snapshot, .decision-panel,
        .top-business-card, .input-card, .result-shell {
            border: 1px solid rgba(16, 32, 51, 0.10);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.96);
            box-shadow: 0 10px 26px rgba(16, 32, 51, 0.06);
            margin: 12px 0 18px;
            padding: 20px;
        }

        .lookup-panel {
            background:
                linear-gradient(135deg, rgba(22, 119, 255, 0.10), transparent 48%),
                #ffffff;
        }

        .lookup-title {
            color: var(--deep-blue);
            font-size: 1.4rem;
            font-weight: 820;
            margin-bottom: 4px;
        }

        .lookup-subtitle {
            color: var(--muted);
            margin-bottom: 12px;
        }

        .customer-snapshot {
            background: #f8fbff;
        }

        .snapshot-grid, .decision-grid {
            display: grid;
            gap: 12px;
        }

        .snapshot-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .snapshot-item {
            border-radius: 14px;
            background: #ffffff;
            border: 1px solid rgba(16, 32, 51, 0.08);
            padding: 12px;
        }

        .decision-panel {
            background: linear-gradient(135deg, #ffffff, #f5faff);
        }

        .decision-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .decision-card {
            border-radius: 18px;
            border: 1px solid rgba(16, 32, 51, 0.10);
            background: #ffffff;
            padding: 16px;
            min-height: 126px;
        }

        .decision-card.high,
        .decision-card.overage {
            background: #fff5f5;
            border-color: rgba(217, 45, 32, 0.22);
        }

        .decision-card.medium {
            background: #fff8ed;
            border-color: rgba(247, 144, 9, 0.24);
        }

        .decision-card.low {
            background: #f0fbf4;
            border-color: rgba(18, 183, 106, 0.22);
        }

        .decision-label {
            color: var(--muted);
            font-size: 0.86rem;
            margin-bottom: 7px;
        }

        .decision-value {
            color: var(--ink);
            font-size: 1.28rem;
            font-weight: 820;
            line-height: 1.25;
        }

        .decision-desc {
            color: #667085;
            font-size: 0.86rem;
            line-height: 1.45;
            margin-top: 8px;
        }

        .top-business-card {
            background:
                linear-gradient(135deg, rgba(22, 119, 255, 0.12), transparent 42%),
                linear-gradient(120deg, #ffffff, #f1fbf6);
            border-color: rgba(18, 183, 106, 0.22);
        }

        .top-business-badge {
            display: inline-flex;
            padding: 5px 10px;
            color: #087443;
            background: #eaf8f0;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 760;
        }

        .top-business-title {
            color: var(--deep-blue);
            font-size: 1.45rem;
            font-weight: 840;
            margin: 10px 0;
        }

        .input-card {
            padding: 16px;
        }

        .chip-blue {
            background: var(--soft-blue);
            color: #1250a5;
        }

        .chip-green {
            background: var(--soft-green);
            color: #087443;
        }

        .chip-orange {
            background: var(--soft-orange);
            color: #b15c00;
        }

        .chip-red {
            background: var(--soft-red);
            color: #c21d1d;
        }

        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.90);
            border: 1px solid rgba(16, 32, 51, 0.10);
            border-radius: 14px;
            padding: 12px 14px;
        }

        .app-shell, .app-header, .nav-shell, .command-bar,
        .customer-360, .decision-center, .panel,
        .risk-queue-card, .empty-state {
            border: 1px solid var(--line);
            border-radius: var(--radius-lg);
            background: var(--surface);
            box-shadow: var(--shadow-sm);
        }

        .app-shell {
            padding: 0;
            background: transparent;
            border: 0;
            box-shadow: none;
        }

        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
            padding: 20px 24px;
            margin-bottom: 14px;
        }

        .brand-title {
            color: var(--navy);
            font-size: 1.7rem;
            font-weight: 860;
            line-height: 1.15;
        }

        .brand-subtitle {
            color: var(--muted);
            font-size: 0.92rem;
            margin-top: 4px;
        }

        .status-cluster {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
        }

        .nav-shell {
            padding: 8px 12px;
            margin: 0 0 16px;
        }

        .nav-shell div[role="radiogroup"],
        div[role="radiogroup"] {
            display: flex;
            gap: 8px;
        }

        .nav-shell label,
        div[role="radiogroup"] label {
            background: #f8fafc;
            border: 1px solid transparent;
            border-radius: 999px;
            padding: 8px 14px;
            transition: all 180ms ease;
        }

        .nav-shell label:hover,
        div[role="radiogroup"] label:hover {
            transform: translateY(-1px);
            background: #eef6ff;
            border-color: rgba(22, 119, 255, 0.22);
        }

        .command-bar {
            padding: 22px;
            margin-bottom: 14px;
            border-color: rgba(22, 119, 255, 0.22);
        }

        .command-title, .panel-title {
            color: var(--navy);
            font-size: 1.2rem;
            font-weight: 820;
            margin-bottom: 3px;
        }

        .panel-subtitle, .muted-text {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .demo-chip-row {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 10px;
        }

        .customer-360, .decision-center, .panel,
        .risk-queue-card {
            padding: 18px;
            margin: 12px 0 16px;
        }

        .snapshot-grid, .decision-kpi-grid, .policy-grid,
        .workspace-grid {
            display: grid;
            gap: 12px;
        }

        .snapshot-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
        }

        .snapshot-card, .kpi-card {
            border: 1px solid var(--line);
            border-radius: var(--radius-md);
            background: #ffffff;
            padding: 14px;
            transition: all 180ms ease;
        }

        .snapshot-card:hover, .kpi-card:hover, .policy-card:hover,
        .top-recommendation:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-sm);
        }

        .snapshot-label, .kpi-label {
            color: var(--muted);
            font-size: 0.8rem;
            margin-bottom: 6px;
        }

        .snapshot-value, .kpi-value {
            color: var(--ink);
            font-size: 1.1rem;
            font-weight: 820;
            line-height: 1.25;
        }

        .decision-center {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
        }

        .decision-hero {
            border-radius: var(--radius-lg);
            border: 1px solid rgba(22, 119, 255, 0.18);
            background: #f4f9ff;
            padding: 18px;
        }

        .decision-kpi-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
            margin-top: 12px;
        }

        .kpi-card.danger, .snapshot-card.danger {
            background: var(--risk-red-bg);
            border-color: rgba(217, 45, 32, 0.22);
        }

        .kpi-card.warning, .snapshot-card.warning {
            background: var(--warn-bg);
            border-color: rgba(247, 144, 9, 0.24);
        }

        .kpi-card.success, .snapshot-card.success {
            background: var(--success-bg);
            border-color: rgba(18, 183, 106, 0.22);
        }

        .kpi-card.neutral, .snapshot-card.neutral {
            background: #f8fafc;
            border-color: var(--line);
        }

        .top-recommendation {
            border-radius: var(--radius-lg);
            border: 1px solid rgba(22, 119, 255, 0.18);
            background: linear-gradient(135deg, #ffffff 0%, #eef6ff 100%);
            padding: 18px;
            margin: 10px 0 14px;
            transition: all 180ms ease;
        }

        .policy-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .script-timeline {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .script-step {
            border-left: 4px solid var(--brand);
            border-radius: var(--radius-md);
            background: #ffffff;
            border-top: 1px solid var(--line);
            border-right: 1px solid var(--line);
            border-bottom: 1px solid var(--line);
            padding: 14px;
        }

        .empty-state {
            padding: 36px 24px;
            text-align: center;
            color: var(--muted);
        }

        .chip.blue, .chip-blue {
            background: #eef6ff;
            color: #1250a5;
        }

        .chip.green, .chip-green {
            background: var(--success-bg);
            color: #087443;
        }

        .chip.orange, .chip-orange {
            background: var(--warn-bg);
            color: #b54708;
        }

        .chip.red, .chip-red {
            background: var(--risk-red-bg);
            color: var(--risk-red);
        }

        .chip.gray {
            background: #f2f4f7;
            color: #475467;
        }

        @media (max-width: 1100px) {
            .summary-grid,
            .snapshot-grid,
            .decision-grid,
            .decision-kpi-grid,
            .policy-grid,
            .script-timeline {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 720px) {
            .summary-grid,
            .snapshot-grid,
            .decision-grid,
            .decision-kpi-grid,
            .policy-grid,
            .script-timeline {
                grid-template-columns: 1fr;
            }

            .app-header {
                align-items: flex-start;
                flex-direction: column;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            * {
                transition: none !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _initialize_session_state() -> None:
    """初始化本次演示统计状态。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    defaults: dict[str, Any] = {
        "total_cases": 0,
        "high_risk_cases": 0,
        "llm_success_count": 0,
        "fallback_count": 0,
        "elapsed_total": 0.0,
        "complaint_type_counter": {},
        "policy_counter": {},
        "history": [],
        "last_result": None,
        "phone_input": "",
        "current_customer": None,
        "customer_lookup_status": "",
        "customer_lookup_phone": "",
        "last_complaint_for_result": "",
        "complaint_input": "",
        "monthly_fee_input": 39,
        "customer_type_input": "存量",
        "tenure_years_input": 2.0,
        "has_broadband_input": False,
        "wants_device_input": False,
        "family_mobile_count_input": 1,
        "wants_port_out_input": False,
        "use_llm_input": True,
        "demo_case_select": "",
        "policy_query": "",
        "policy_category_filter": "全部",
        "active_page": "workbench",
        "dashboard_status_filter": "全部",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _stop_if_policy_file_missing() -> None:
    """在政策库缺失时给出清晰提示并停止页面。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    if not (DATA_DIR / "policies.json").exists():
        st.error("缺少 data/policies.json，请先生成政策库。")
        st.stop()


def _render_app_shell_header(settings: dict[str, object]) -> None:
    """渲染企业工作台顶部壳层。

    Args:
        settings: LLM 配置。

    Returns:
        无返回值。
    """

    configured = is_llm_configured()
    model_status = "云端模型 已配置" if configured else "云端模型 未配置"
    model_tone = "green" if configured else "orange"
    status_html = "".join(
        [
            _badge(model_status, model_tone),
            _badge(settings.get("model", "未知模型"), "blue"),
            _badge(f"超时 {settings.get('timeout', '-')} 秒", "gray"),
            _badge(f"本次处理 {st.session_state['total_cases']}", "blue"),
            _badge(f"高风险 {st.session_state['high_risk_cases']}", "red"),
        ]
    )
    st.markdown(
        f"""
        <div class="app-shell">
            <div class="app-header">
                <div class="brand-block">
                    <div class="brand-title">客户拯救者</div>
                    <div class="brand-subtitle">
                        The Client Savior｜投诉秒变留人机会，政策套餐自动配对
                    </div>
                </div>
                <div class="status-cluster">{status_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_top_navigation() -> str:
    """渲染工作台顶部导航。

    Args:
        无参数。

    Returns:
        当前选中的页面键。
    """

    options = {
        "客服工作台": "workbench",
        "风险看板": "dashboard",
        "政策库": "policies",
    }
    current_key = str(st.session_state.get("active_page", "workbench"))
    reverse_options = {value: key for key, value in options.items()}
    current_label = reverse_options.get(current_key, "客服工作台")
    selected_label = st.radio(
        "主导航",
        list(options),
        index=list(options).index(current_label),
        key="active_page_label",
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_page = options[selected_label]
    st.session_state["active_page"] = selected_page
    return selected_page


def _render_hero() -> None:
    """渲染产品级首页 Hero 区。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">The Client Savior｜客户拯救者</div>
            <div class="hero-subtitle">投诉秒变留人机会，政策套餐自动配对</div>
            <div class="policy-meta">
                三步完成：录入投诉 → 云端模型分析 → 生成挽留方案
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_step_cards()


def _render_step_cards() -> None:
    """渲染三步演示流程卡片。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    steps = [
        ("① 输入投诉", "粘贴客户原话，选择基础画像。"),
        ("② 模型分析", "本地召回政策，云端模型生成方案。"),
        ("③ 一线执行", "输出推荐政策、挽留话术、办理提醒。"),
    ]
    columns = st.columns(3)
    for column, (title, body) in zip(columns, steps, strict=False):
        with column:
            st.markdown(
                f"""
                <div class="step-card">
                    <b>{html.escape(title)}</b>
                    <span>{html.escape(body)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_sidebar(settings: dict[str, object]) -> None:
    """渲染侧边栏配置、统计和现场提示。

    Args:
        settings: LLM 配置。

    Returns:
        无返回值。
    """

    configured = is_llm_configured()
    status_text = "已配置" if configured else "未配置"
    status_kind = "llm" if configured else "fallback"

    st.sidebar.markdown("### 运行状态")
    st.sidebar.markdown(
        _render_status_badge(status_text, status_kind),
        unsafe_allow_html=True,
    )
    st.sidebar.write(f"当前模型：`{settings['model']}`")
    st.sidebar.write(f"超时时间：`{settings['timeout']}` 秒")
    with st.sidebar.expander("Base URL", expanded=False):
        st.code(str(settings["base_url"]))
    if st.sidebar.button("LLM 连通性测试", width="stretch"):
        _run_llm_connectivity_test()

    st.sidebar.divider()
    st.sidebar.markdown("### 演示统计")
    st.sidebar.metric("总处理数", st.session_state["total_cases"])
    st.sidebar.metric("云端模型生成次数", st.session_state["llm_success_count"])
    st.sidebar.metric("本地模板兜底次数", st.session_state["fallback_count"])
    _render_sidebar_last_result()

    st.sidebar.divider()
    st.sidebar.markdown("### 现场提示")
    if configured:
        st.sidebar.info("推荐先点击连通性测试，确认云端模型可用。")
    else:
        st.sidebar.warning("未配置有效 API Key 时系统会走本地模板兜底。")


def _run_llm_connectivity_test() -> None:
    """运行侧边栏 LLM 连通性测试。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    try:
        with st.sidebar.spinner("正在测试 LLM 连通性。"):
            result = test_llm_connection()
        st.sidebar.success(
            f"LLM 连通正常，耗时 {float(result['elapsed_seconds']):.2f} 秒。"
        )
    except Exception as exc:
        st.sidebar.error(f"失败原因：{str(exc)[:120]}")


def _render_sidebar_last_result() -> None:
    """在侧边栏展示最近一次生成元信息。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    last_result = st.session_state.get("last_result")
    if not isinstance(last_result, AgentResult):
        return

    analysis = last_result.customer_analysis
    mode_text = "云端模型生成" if last_result.mode == "llm" else "本地模板兜底"
    cache_text = "是" if last_result.cached else "否"
    st.sidebar.divider()
    st.sidebar.markdown("### 最近一次结果")
    st.sidebar.write(f"当前模式：`{mode_text}`")
    st.sidebar.write(f"模型：`{last_result.model}`")
    st.sidebar.write(f"投诉类型：`{analysis.get('complaint_type', '其他')}`")
    st.sidebar.write(f"耗时：`{last_result.elapsed_seconds:.2f} 秒`")
    st.sidebar.write(f"缓存：`{cache_text}`")
    if last_result.llm_error:
        st.sidebar.warning(f"失败原因：{last_result.llm_error}")


def _render_workbench_page(
    policies: list[dict[str, object]],
    demo_cases: list[dict[str, object]],
    customers: list[dict[str, object]],
) -> None:
    """渲染一线客服挽留工作台。

    Args:
        policies: 政策卡列表。
        demo_cases: 演示案例列表。
        customers: 本地演示客户画像列表。

    Returns:
        无返回值。
    """

    _render_number_command_bar(customers, demo_cases)
    current_customer = _safe_get_current_customer()
    _render_customer_360(current_customer)
    complaint = str(st.session_state.get("complaint_input", ""))
    decision_slot = st.empty()

    left_column, right_column = st.columns([0.36, 0.64], gap="large")
    with left_column:
        submitted = _render_intake_panel()
        if submitted:
            _handle_generation(policies)
            last_result = st.session_state.get("last_result")
            if not isinstance(last_result, AgentResult):
                last_result = None
        clear_col, next_col = st.columns(2)
        with clear_col:
            st.button("清空输入", width="stretch", on_click=_clear_current_case)
        with next_col:
            st.button("处理下一条", width="stretch", on_click=_clear_current_case)

    current_customer = _safe_get_current_customer()
    complaint = str(st.session_state.get("complaint_input", ""))
    last_result = st.session_state.get("last_result")
    if not isinstance(last_result, AgentResult):
        last_result = None
    with decision_slot.container():
        _render_decision_command_center(last_result, complaint, current_customer)
    with right_column:
        _render_recommendation_workspace(last_result)


def _render_number_command_bar(
    customers: list[dict[str, object]],
    demo_cases: list[dict[str, object]],
) -> None:
    """渲染号码查询 Command Bar。

    Args:
        customers: 本地演示客户画像列表。
        demo_cases: 演示案例列表。

    Returns:
        无返回值。
    """

    st.markdown(
        """
        <div class="command-bar">
            <div class="command-title">号码查询</div>
            <div class="panel-subtitle">
                输入客户手机号，带出本地演示画像；手机号仅用于本地看板，不传入模型。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    input_col, query_col, clear_col, test_col = st.columns([0.65, 0.15, 0.10, 0.10])
    with input_col:
        st.text_input(
            "输入客户手机号",
            placeholder="请输入 11 位手机号，例如 13800138001",
            key="phone_input",
        )
    with query_col:
        if st.button("查询客户", type="primary", width="stretch"):
            _handle_customer_lookup(customers)
    with clear_col:
        st.button("清空", width="stretch", on_click=_clear_lookup_state)
    with test_col:
        if st.button("测模型", width="stretch"):
            _run_llm_connectivity_test()

    status = str(st.session_state.get("customer_lookup_status", ""))
    if status:
        if _safe_get_current_customer():
            st.success(f"{status}：{_mask_phone(_normalize_phone(st.session_state.get('phone_input', '')))}")
        else:
            st.warning(status)

    if demo_cases:
        st.markdown('<div class="demo-chip-row"><span class="muted-text">演示号码：</span></div>', unsafe_allow_html=True)
        columns = st.columns(min(6, len(demo_cases)))
        for index, demo_case in enumerate(demo_cases[:6]):
            label = _short_case_label(str(demo_case.get("name", "")))
            with columns[index % len(columns)]:
                st.button(
                    label,
                    key=f"command_demo_{index}",
                    width="stretch",
                    on_click=_apply_demo_case,
                    args=(demo_case,),
                )


def _render_customer_360(customer: dict[str, object] | None) -> None:
    """渲染客户 360 快照。

    Args:
        customer: 本地客户画像。

    Returns:
        无返回值。
    """

    if customer is None:
        _empty_state("客户 360", "未查询到客户画像，可继续手动录入投诉与画像。")
        return

    overage_fee = _as_float(customer.get("overage_fee")) or 0
    wants_port_out = bool(customer.get("wants_port_out"))
    value_level = _customer_value_level(customer)
    items = [
        ("手机号", _mask_phone(_normalize_phone(customer.get("phone"))), "neutral"),
        ("客户类型", customer.get("customer_type", "未知"), "neutral"),
        ("当前套餐", customer.get("plan_name", "未知套餐"), "blue"),
        ("当前月租", f"{customer.get('monthly_fee', 0)} 元", "neutral"),
        ("网龄", f"{customer.get('tenure_years', 0)} 年", "neutral"),
        ("套餐流量", f"{customer.get('plan_data_gb', '-')}G", "neutral"),
        ("上月用量", f"{customer.get('last_month_usage_gb', '-')}G", "neutral"),
        ("超耗费用", f"{overage_fee:g} 元", "danger" if overage_fee > 0 else "success"),
        ("家庭号码数", customer.get("family_mobile_count", 0), "neutral"),
        ("宽带状态", "宽带用户" if customer.get("has_broadband") else "未装宽带", "blue"),
        ("携转意向", "有携转风险" if wants_port_out else "暂无", "danger" if wants_port_out else "success"),
        ("客户价值", value_level, "warning" if value_level == "高价值" else "neutral"),
    ]
    cards = "".join(_snapshot_card(label, value, tone) for label, value, tone in items)
    st.markdown(
        f"""
        <div class="customer-360">
            <div class="panel-header">
                <div class="panel-title">客户 360 Snapshot</div>
                <div class="panel-subtitle">
                    {_html_escape(customer.get("recommended_hint", ""))}
                </div>
            </div>
            <div class="snapshot-grid">{cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_decision_command_center(
    result: AgentResult | None,
    complaint: str,
    customer: dict[str, object] | None,
) -> None:
    """渲染 AI 决策驾驶舱。

    Args:
        result: 智能体结果。
        complaint: 客户投诉原文。
        customer: 本地客户画像。

    Returns:
        无返回值。
    """

    summary = _build_decision_summary(result, complaint, customer)
    business = summary["business"]
    overage = summary["overage"]
    risk_level = str(summary["risk_level"])
    complaint_type = str(summary["complaint_type"])
    emotion = str(summary["emotion"])
    priority = str(summary["follow_priority"])
    hero_desc = str(business.get("reason", "输入投诉后自动生成推荐业务。"))
    kpis = [
        _metric_card(
            "是否超耗",
            overage.get("label", "暂无数据"),
            overage.get("reason", ""),
            _overage_tone(str(overage.get("status", ""))),
        ),
        _metric_card("风险等级", _display_pending(risk_level), "用于安排跟进节奏", _risk_tone(risk_level)),
        _metric_card("投诉类型", _display_pending(complaint_type), "用于匹配政策场景", "neutral"),
        _metric_card("客户情绪", _display_pending(emotion), "辅助判断沟通语气", _emotion_tone(emotion)),
        _metric_card("跟进优先级", _display_pending(priority), "P1 需优先处理", _priority_tone(priority)),
    ]
    st.markdown(
        f"""
        <div class="decision-center">
            <div class="panel-header">
                <div class="panel-title">AI 决策驾驶舱</div>
                <div class="panel-subtitle">优先看风险、超耗和首推业务，再执行话术。</div>
            </div>
            <div class="decision-hero">
                <div class="kpi-label">首推业务</div>
                <div class="top-business-title">{_html_escape(business.get("title", "待生成"))}</div>
                <div class="policy-meta">
                    {_html_escape(business.get("category", "暂无"))}
                    ｜ {_html_escape(business.get("price", ""))}
                </div>
                <div class="muted-text">{_html_escape(hero_desc)}</div>
            </div>
            <div class="decision-kpi-grid">{''.join(kpis)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_intake_panel() -> bool:
    """渲染投诉录入与画像补充面板。

    Args:
        无参数。

    Returns:
        用户是否提交表单。
    """

    with st.form("case_form"):
        _section_header(
            "投诉录入",
            "粘贴客户原话，模型不会接收手机号。",
        )
        st.markdown(
            """
            <div class="field-label-row">
                <span>投诉内容</span>
                <span class="voice-tooltip">
                    <button class="voice-button" type="button">语音输入</button>
                    <span class="voice-tooltip-text">开发中，敬请期待</span>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area(
            "投诉内容",
            height=170,
            placeholder="请粘贴客户原话，例如：这个套餐越来越贵，不行我就携号转网了。",
            key="complaint_input",
            label_visibility="collapsed",
        )
        _section_header("画像补充", "查询命中后会自动带入，可人工修正。")
        col_left, col_right = st.columns(2)
        with col_left:
            st.number_input(
                "当前月租",
                min_value=0,
                max_value=999,
                step=1,
                key="monthly_fee_input",
            )
            st.selectbox("客户类型", CUSTOMER_TYPES, key="customer_type_input")
            st.slider(
                "网龄",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                key="tenure_years_input",
            )
            st.slider(
                "家庭号码数",
                min_value=0,
                max_value=20,
                step=1,
                key="family_mobile_count_input",
            )
        with col_right:
            st.checkbox("已有宽带", key="has_broadband_input")
            st.checkbox("有换机需求", key="wants_device_input")
            st.checkbox("明确携转/离网", key="wants_port_out_input")
            st.checkbox("启用云端模型", key="use_llm_input")
        return st.form_submit_button(
            "生成客户挽留方案",
            type="primary",
            width="stretch",
        )


def _render_recommendation_workspace(result: AgentResult | None) -> None:
    """渲染推荐方案与话术工作区。

    Args:
        result: 智能体结果。

    Returns:
        无返回值。
    """

    if result is None:
        _empty_state(
            "等待 AI 生成方案",
            "输入号码与投诉后，AI 将生成推荐业务、政策 Top 3、四段式话术和办理提醒。流程：号码查询 → 客户画像 → 模型分析 → 输出方案。",
        )
        return

    _render_generation_status_bar(result)
    if result.llm_error:
        st.markdown(
            f"""
            <div class="warning-strip">
                云端模型调用异常，已切换本地模板兜底：{_html_escape(result.llm_error)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    _render_top_business_card(result)
    _render_recommended_policies(result.recommended_policies)
    _render_script_cards(result.retention_script)
    _render_note_cards(result.internal_notes)
    st.download_button(
        "下载方案 Markdown",
        data=build_result_markdown(result),
        file_name="client_savior_result.md",
        mime="text/markdown",
        width="stretch",
    )


def _snapshot_card(label: object, value: object, tone: str = "neutral") -> str:
    """生成客户快照卡片。

    Args:
        label: 标签。
        value: 主值。
        tone: 颜色语义。

    Returns:
        HTML 卡片字符串。
    """

    return f"""
    <div class="snapshot-card {html.escape(tone)}">
        <div class="snapshot-label">{_html_escape(label)}</div>
        <div class="snapshot-value">{_html_escape(value)}</div>
    </div>
    """


def _display_pending(value: str) -> str:
    """把未生成状态转换为待分析文案。

    Args:
        value: 原始展示值。

    Returns:
        待分析或原值。
    """

    return "待分析" if value in {"待生成", ""} else value


def _overage_tone(status: str) -> str:
    """按超耗状态返回色彩语义。

    Args:
        status: 超耗状态。

    Returns:
        色彩语义。
    """

    if status == "是":
        return "danger"
    if status == "疑似":
        return "warning"
    if status == "否":
        return "success"
    return "neutral"


def _risk_tone(risk_level: str) -> str:
    """按风险等级返回色彩语义。

    Args:
        risk_level: 风险等级。

    Returns:
        色彩语义。
    """

    score = _risk_score(risk_level)
    if score == 3:
        return "danger"
    if score == 2:
        return "warning"
    if score == 1:
        return "success"
    return "neutral"


def _emotion_tone(emotion: str) -> str:
    """按客户情绪返回色彩语义。

    Args:
        emotion: 情绪文本。

    Returns:
        色彩语义。
    """

    if any(keyword in emotion for keyword in ("强烈", "不满", "焦虑")):
        return "warning"
    return "neutral"


def _priority_tone(priority: str) -> str:
    """按跟进优先级返回色彩语义。

    Args:
        priority: 优先级。

    Returns:
        色彩语义。
    """

    if priority == "P1":
        return "danger"
    if priority == "P2":
        return "warning"
    if priority == "P3":
        return "success"
    return "neutral"


def _render_case_tab(
    policies: list[dict[str, object]],
    demo_cases: list[dict[str, object]],
) -> None:
    """渲染客服工作台式投诉处理页。

    Args:
        policies: 政策卡列表。
        demo_cases: 演示案例列表。

    Returns:
        无返回值。
    """

    customers = load_customers()
    _render_number_lookup_panel(demo_cases, customers)
    _render_demo_shortcuts(demo_cases)

    current_customer = _safe_get_current_customer()
    if current_customer:
        _render_customer_snapshot(current_customer)

    left_column, right_column = st.columns([0.38, 0.62], gap="large")
    with left_column:
        st.markdown(
            '<div class="section-title">投诉与画像补充</div>',
            unsafe_allow_html=True,
        )
        submitted = _render_case_form()
        clear_left, clear_right = st.columns(2)
        with clear_left:
            st.button(
                "清空输入",
                width="stretch",
                on_click=_clear_current_case,
            )
        with clear_right:
            st.button(
                "处理下一条",
                width="stretch",
                on_click=_clear_current_case,
            )

    if submitted:
        _handle_generation(policies)

    with right_column:
        st.markdown(
            '<div class="section-title">智能分析结果</div>',
            unsafe_allow_html=True,
        )
        last_result = st.session_state.get("last_result")
        if isinstance(last_result, AgentResult):
            _render_agent_result(last_result)
        else:
            _render_decision_summary_panel(
                None,
                str(st.session_state.get("complaint_input", "")),
                current_customer,
            )
            _render_result_placeholder()


def _render_number_lookup_panel(
    demo_cases: list[dict[str, object]],
    customers: list[dict[str, object]],
) -> None:
    """渲染号码查询工作台入口。

    Args:
        demo_cases: 演示案例列表。
        customers: 本地演示客户画像列表。

    Returns:
        无返回值。
    """

    del demo_cases
    st.markdown(
        """
        <div class="lookup-panel">
            <div class="lookup-title">号码查询</div>
            <div class="lookup-subtitle">
                输入客户手机号，快速带出客户画像与风险提示
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    input_col, query_col, clear_col = st.columns([0.64, 0.18, 0.18])
    with input_col:
        st.text_input(
            "输入客户手机号",
            placeholder="请输入 11 位手机号，例如 13800138000",
            key="phone_input",
        )
    with query_col:
        if st.button("查询客户", type="primary", width="stretch"):
            _handle_customer_lookup(customers)
    with clear_col:
        if st.button("清空", width="stretch"):
            _clear_lookup_state()
            st.rerun()

    status = str(st.session_state.get("customer_lookup_status", ""))
    if status:
        if _safe_get_current_customer():
            st.success(status)
        else:
            st.warning(status)


def _handle_customer_lookup(customers: list[dict[str, object]]) -> None:
    """处理本地客户号码查询。

    Args:
        customers: 本地演示客户画像列表。

    Returns:
        无返回值。
    """

    phone = _normalize_phone(st.session_state.get("phone_input", ""))
    st.session_state["customer_lookup_phone"] = phone
    if not phone:
        st.session_state["current_customer"] = None
        st.session_state["customer_lookup_status"] = "请输入手机号后查询。"
        return
    if not phone.isdigit() or len(phone) != 11:
        st.session_state["current_customer"] = None
        st.session_state["customer_lookup_status"] = (
            "手机号格式不正确，请输入 11 位手机号；也可以继续手动补充画像。"
        )
        return

    customer = _find_customer_by_phone(phone, customers)
    if customer is None:
        st.session_state["current_customer"] = None
        st.session_state["customer_lookup_status"] = (
            "未查询到客户，可手动补充画像"
        )
        return

    _apply_customer_profile(customer)
    st.session_state["current_customer"] = customer
    st.session_state["customer_lookup_status"] = "命中客户画像"


def _clear_lookup_state() -> None:
    """清空号码查询状态和当前客户画像。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.session_state["phone_input"] = ""
    st.session_state["current_customer"] = None
    st.session_state["customer_lookup_status"] = ""
    st.session_state["customer_lookup_phone"] = ""


def _find_customer_by_phone(
    phone: str,
    customers: list[dict[str, object]],
) -> dict[str, object] | None:
    """按手机号查找本地演示客户。

    Args:
        phone: 标准化后的手机号。
        customers: 本地演示客户画像列表。

    Returns:
        命中的客户画像；未命中时返回 None。
    """

    for customer in customers:
        if _normalize_phone(customer.get("phone")) == phone:
            return dict(customer)
    return None


def _apply_customer_profile(customer: dict[str, object]) -> None:
    """把本地客户画像写入当前输入状态。

    Args:
        customer: 本地演示客户画像。

    Returns:
        无返回值。
    """

    st.session_state["monthly_fee_input"] = int(customer.get("monthly_fee", 39))
    st.session_state["customer_type_input"] = str(
        customer.get("customer_type", "存量")
    )
    st.session_state["tenure_years_input"] = float(
        customer.get("tenure_years", 2)
    )
    st.session_state["has_broadband_input"] = bool(
        customer.get("has_broadband", False)
    )
    st.session_state["wants_device_input"] = bool(
        customer.get("wants_device", False)
    )
    st.session_state["family_mobile_count_input"] = int(
        customer.get("family_mobile_count", 1)
    )
    st.session_state["wants_port_out_input"] = bool(
        customer.get("wants_port_out", False)
    )


def _render_customer_snapshot(customer: dict[str, object]) -> None:
    """渲染号码查询后的客户概览。

    Args:
        customer: 本地演示客户画像。

    Returns:
        无返回值。
    """

    items = [
        ("手机号", _mask_phone(_normalize_phone(customer.get("phone")))),
        ("客户类型", str(customer.get("customer_type", "未知"))),
        ("当前月租", f"{customer.get('monthly_fee', 0)} 元"),
        ("网龄", f"{customer.get('tenure_years', 0)} 年"),
        ("已有宽带", "是" if customer.get("has_broadband") else "否"),
        ("家庭号码数", str(customer.get("family_mobile_count", 0))),
        ("携转风险", "是" if customer.get("wants_port_out") else "否"),
        ("当前套餐", str(customer.get("plan_name", "未知套餐"))),
    ]
    cells = "".join(
        f"""
        <div class="snapshot-item">
            <div class="decision-label">{html.escape(label)}</div>
            <div class="decision-value">{html.escape(value)}</div>
        </div>
        """
        for label, value in items
    )
    st.markdown(
        f"""
        <div class="customer-snapshot">
            <div class="section-title">客户概览</div>
            <div class="snapshot-grid">{cells}</div>
            <div class="decision-desc">
                {html.escape(str(customer.get("recommended_hint", "")))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_demo_shortcuts(demo_cases: list[dict[str, object]]) -> None:
    """渲染演示号码和演示案例快捷入口。

    Args:
        demo_cases: 演示案例列表。

    Returns:
        无返回值。
    """

    if not demo_cases:
        st.caption("未找到演示案例，可直接手动录入投诉。")
        return

    columns = st.columns(min(6, len(demo_cases)))
    for index, demo_case in enumerate(demo_cases):
        label = _short_case_label(str(demo_case.get("name", "")))
        with columns[index % len(columns)]:
            st.button(
                label,
                key=f"demo_case_button_{index}",
                width="stretch",
                on_click=_apply_demo_case,
                args=(demo_case,),
            )

    case_names = [str(case.get("name", "")) for case in demo_cases]
    selected_name = st.selectbox(
        "选择演示案例",
        case_names,
        key="demo_case_select",
    )
    if st.button("一键填充选中案例", width="stretch"):
        selected_case = next(
            case for case in demo_cases if case.get("name") == selected_name
        )
        _apply_demo_case(selected_case)
        st.rerun()


def _apply_demo_case(demo_case: dict[str, object]) -> None:
    """把演示案例写入当前输入状态。

    Args:
        demo_case: 单个演示案例。

    Returns:
        无返回值。
    """

    profile = demo_case.get("profile", {})
    if not isinstance(profile, dict):
        profile = {}
    phone = _normalize_phone(demo_case.get("phone", ""))
    st.session_state["phone_input"] = phone
    customer = _find_customer_by_phone(phone, load_customers()) if phone else None
    if customer is not None:
        _apply_customer_profile(customer)
        st.session_state["current_customer"] = customer
        st.session_state["customer_lookup_status"] = "命中客户画像"
        st.session_state["customer_lookup_phone"] = phone
    else:
        st.session_state["current_customer"] = None
        st.session_state["customer_lookup_status"] = (
            "未查询到客户，可手动补充画像" if phone else ""
        )
        st.session_state["customer_lookup_phone"] = phone
        _apply_profile_from_demo(profile)
    st.session_state["complaint_input"] = str(demo_case.get("complaint", ""))
    st.session_state["last_result"] = None


def _apply_profile_from_demo(profile: dict[str, object]) -> None:
    """把演示案例画像写入当前输入状态。

    Args:
        profile: 演示案例画像。

    Returns:
        无返回值。
    """

    st.session_state["monthly_fee_input"] = int(profile.get("monthly_fee", 39))
    st.session_state["customer_type_input"] = str(
        profile.get("customer_type", "存量")
    )
    st.session_state["tenure_years_input"] = float(profile.get("tenure_years", 2))
    st.session_state["has_broadband_input"] = bool(
        profile.get("has_broadband", False)
    )
    st.session_state["wants_device_input"] = bool(
        profile.get("wants_device", False)
    )
    st.session_state["family_mobile_count_input"] = int(
        profile.get("family_mobile_count", 1)
    )
    st.session_state["wants_port_out_input"] = bool(
        profile.get("wants_port_out", False)
    )


def _short_case_label(case_name: str) -> str:
    """生成适合按钮展示的短案例名。

    Args:
        case_name: 原始案例名。

    Returns:
        短按钮文案。
    """

    mapping = {
        "套餐太贵想携转": "套餐太贵想携转",
        "流量不够刷视频": "流量不够刷视频",
        "宽带/WiFi网速差": "宽带 WiFi 差",
        "想换手机但觉得贵": "想换手机",
        "家庭号码多想省钱": "家庭号码多",
        "商户需要宽带和宣传触达": "商户宽带宣传",
    }
    return mapping.get(case_name, case_name[:8] or "演示案例")


def _clear_current_case() -> None:
    """清空当前输入和结果，不影响历史看板。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.session_state["complaint_input"] = ""
    st.session_state["phone_input"] = ""
    st.session_state["current_customer"] = None
    st.session_state["customer_lookup_status"] = ""
    st.session_state["customer_lookup_phone"] = ""
    st.session_state["last_complaint_for_result"] = ""
    st.session_state["monthly_fee_input"] = 39
    st.session_state["customer_type_input"] = "存量"
    st.session_state["tenure_years_input"] = 2.0
    st.session_state["has_broadband_input"] = False
    st.session_state["wants_device_input"] = False
    st.session_state["family_mobile_count_input"] = 1
    st.session_state["wants_port_out_input"] = False
    st.session_state["use_llm_input"] = True
    st.session_state["last_result"] = None


def _render_case_form() -> bool:
    """渲染客户投诉输入表单。

    Args:
        无参数。

    Returns:
        用户是否提交表单。
    """

    with st.form("case_form"):
        st.markdown('<div class="input-card">', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="field-label-row">
                <span>投诉内容</span>
                <span class="voice-tooltip">
                    <button
                        class="voice-button"
                        type="button"
                    >
                        语音输入
                    </button>
                    <span class="voice-tooltip-text">开发中，敬请期待</span>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.text_area(
            "投诉内容",
            height=160,
            placeholder="请输入客户投诉原文。",
            key="complaint_input",
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)
        col_left, col_right = st.columns(2)
        with col_left:
            st.number_input(
                "当前套餐月租",
                min_value=0,
                max_value=999,
                step=1,
                key="monthly_fee_input",
            )
            st.selectbox(
                "客户类型",
                CUSTOMER_TYPES,
                key="customer_type_input",
            )
            st.slider(
                "网龄",
                min_value=0.0,
                max_value=30.0,
                step=0.5,
                key="tenure_years_input",
            )
        with col_right:
            st.slider(
                "家庭移动号码数",
                min_value=0,
                max_value=20,
                step=1,
                key="family_mobile_count_input",
            )
            st.checkbox("已有宽带", key="has_broadband_input")
            st.checkbox("有换机需求", key="wants_device_input")
            st.checkbox("明确想离网/携转", key="wants_port_out_input")
            st.checkbox("启用云端模型生成", key="use_llm_input")
        return st.form_submit_button("生成客户挽留方案", width="stretch")


def _handle_generation(policies: list[dict[str, object]]) -> None:
    """处理生成按钮提交。

    Args:
        policies: 政策卡列表。

    Returns:
        无返回值。
    """

    complaint = str(st.session_state["complaint_input"]).strip()
    if not complaint:
        st.warning("请先输入投诉内容。")
        return
    raw_phone = st.session_state.get("phone_input", "")
    phone = _normalize_phone(raw_phone)
    if phone and (not phone.isdigit() or len(phone) != 11):
        st.warning("手机号格式不正确，请输入 11 位手机号；也可以留空继续演示。")
        return
    masked_phone = _mask_phone(phone)

    profile = CustomerProfile(
        monthly_fee=int(st.session_state["monthly_fee_input"]),
        customer_type=str(st.session_state["customer_type_input"]),
        tenure_years=float(st.session_state["tenure_years_input"]),
        has_broadband=bool(st.session_state["has_broadband_input"]),
        wants_device=bool(st.session_state["wants_device_input"]),
        family_mobile_count=int(st.session_state["family_mobile_count_input"]),
        wants_port_out=bool(st.session_state["wants_port_out_input"]),
    )
    agent = ClientSaviorAgent(policies)
    st.session_state["last_complaint_for_result"] = complaint
    with st.spinner("云端模型分析中，超时将自动切换本地兜底。"):
        result = agent.run(
            complaint=complaint,
            profile=profile,
            use_llm=bool(st.session_state["use_llm_input"]),
        )
    st.session_state["last_result"] = result
    _update_dashboard(
        result,
        phone=phone,
        masked_phone=masked_phone,
        complaint=complaint,
    )


def _render_result_placeholder() -> None:
    """渲染未生成状态的引导卡片。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.markdown(
        """
        <div class="empty-card">
            <b>等待生成挽留方案</b>
            <span>
                先查询号码或点击演示案例按钮，再补充客户投诉与画像，
                点击“生成客户挽留方案”。这里会展示决策摘要、首推业务、
                推荐政策、四段式话术和内部提醒。
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_agent_result(result: AgentResult) -> None:
    """渲染智能体结果。

    Args:
        result: 智能体输出。

    Returns:
        无返回值。
    """

    complaint = str(st.session_state.get("last_complaint_for_result", ""))
    customer = _safe_get_current_customer()

    _render_decision_summary_panel(result, complaint, customer)
    _render_top_business_card(result)
    if result.llm_error:
        st.markdown(
            f"""
            <div class="warning-strip">
                云端模型调用异常，已切换本地模板兜底：
                {html.escape(result.llm_error)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    _render_recommended_policies(result.recommended_policies)
    _render_script_cards(result.retention_script)
    _render_note_cards(result.internal_notes)
    markdown = build_result_markdown(result)
    st.download_button(
        "下载方案 Markdown",
        data=markdown,
        file_name="client_savior_result.md",
        mime="text/markdown",
        width="stretch",
    )


def _render_status_badge(text: str, kind: str) -> str:
    """生成状态徽标 HTML。

    Args:
        text: 徽标文案。
        kind: 徽标类型。

    Returns:
        已转义文本组成的徽标 HTML。
    """

    class_name = {
        "llm": "status-llm",
        "fallback": "status-fallback",
        "high": "risk-high",
        "medium": "risk-medium",
        "low": "risk-low",
    }.get(kind, "status-llm")
    return (
        f'<span class="status-pill {class_name}">'
        f"{html.escape(text)}</span>"
    )


def _html_escape(value: object) -> str:
    """转义动态文本，避免 unsafe HTML 注入。

    Args:
        value: 任意待展示对象。

    Returns:
        转义后的字符串。
    """

    return html.escape(str(value or ""))


def _badge(text: object, tone: str = "blue") -> str:
    """生成状态徽标。

    Args:
        text: 徽标文案。
        tone: 颜色语义。

    Returns:
        HTML 徽标字符串。
    """

    return f'<span class="status-pill {_tone_class(tone)}">{_html_escape(text)}</span>'


def _chip(text: object, tone: str = "blue") -> str:
    """生成轻量标签。

    Args:
        text: 标签文案。
        tone: 颜色语义。

    Returns:
        HTML 标签字符串。
    """

    return f'<span class="chip {html.escape(tone)}">{_html_escape(text)}</span>'


def _chip_group(items: object, tone: str = "blue", limit: int = 4) -> str:
    """生成标签组。

    Args:
        items: 原始列表或文本。
        tone: 颜色语义。
        limit: 最多展示数量。

    Returns:
        HTML 标签组。
    """

    return "".join(_chip(item, tone) for item in _format_list_items(items, limit))


def _metric_card(
    label: str,
    value: object,
    desc: str = "",
    tone: str = "neutral",
) -> str:
    """生成 KPI 卡片。

    Args:
        label: 指标标签。
        value: 主值。
        desc: 辅助说明。
        tone: 颜色语义。

    Returns:
        HTML 卡片字符串。
    """

    return f"""
    <div class="kpi-card {html.escape(tone)}">
        <div class="kpi-label">{_html_escape(label)}</div>
        <div class="kpi-value">{_html_escape(value)}</div>
        <div class="muted-text">{_html_escape(desc)}</div>
    </div>
    """


def _section_header(title: str, subtitle: str = "") -> None:
    """渲染产品化分区标题。

    Args:
        title: 标题。
        subtitle: 副标题。

    Returns:
        无返回值。
    """

    subtitle_html = (
        f'<div class="panel-subtitle">{_html_escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div class="panel-header">
            <div class="panel-title">{_html_escape(title)}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _empty_state(title: str, body: str) -> None:
    """渲染空状态提示。

    Args:
        title: 空状态标题。
        body: 空状态说明。

    Returns:
        无返回值。
    """

    st.markdown(
        f"""
        <div class="empty-state">
            <div class="panel-title">{_html_escape(title)}</div>
            <div class="panel-subtitle">{_html_escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tone_class(tone: str) -> str:
    """把语义色映射到现有状态样式。

    Args:
        tone: 颜色语义。

    Returns:
        CSS 类名。
    """

    mapping = {
        "blue": "status-llm",
        "green": "status-llm",
        "orange": "status-fallback",
        "red": "risk-high",
        "gray": "chip gray",
    }
    return mapping.get(tone, "status-llm")


def _safe_get_current_customer() -> dict[str, object] | None:
    """安全读取当前本地客户画像。

    Args:
        无参数。

    Returns:
        当前客户画像；没有命中本地演示客户时返回 None。
    """

    customer = st.session_state.get("current_customer")
    if isinstance(customer, dict):
        return dict(customer)
    return None


def _derive_overage_status(
    complaint: str,
    customer: dict[str, object] | None,
    result: AgentResult | None = None,
) -> dict[str, object]:
    """推导客户是否超耗，手机号和客户数据仅用于本地演示。

    Args:
        complaint: 客户投诉原文。
        customer: 本地客户画像。
        result: 智能体结果，当前仅保留接口兼容。

    Returns:
        超耗状态、展示标签、原因、用量和费用文本。
    """

    del result
    keywords = ("超量", "超耗", "流量不够", "月底提醒", "扣费", "流量费")
    complaint_text = str(complaint)
    has_keyword = any(keyword in complaint_text for keyword in keywords)
    plan_data = _as_float((customer or {}).get("plan_data_gb"))
    usage_data = _as_float((customer or {}).get("last_month_usage_gb"))
    fee_value = _as_float((customer or {}).get("overage_fee"))

    status = "未知"
    usage_text = "暂无用量数据"
    fee_text = "暂无超耗费用"
    reason = "暂无用量数据，需查询系统详单。"
    if plan_data is not None and usage_data is not None:
        usage_text = f"上月{usage_data:g}G / 套餐{plan_data:g}G"
        if usage_data > plan_data:
            status = "是"
            reason = "上月使用量已超过套餐内流量，建议优先核查超耗费用。"
        else:
            status = "否"
            reason = "本地演示用量未超过套餐内流量。"
    if fee_value is not None and fee_value > 0:
        fee_text = f"超耗费用{fee_value:g}元"
    if has_keyword and status != "是":
        status = "疑似"
        reason = "投诉内容出现流量或扣费相关表达，建议优先核查详单。"

    label = {
        "是": "已超耗",
        "疑似": "疑似超耗",
        "否": "未发现超耗",
        "未知": "暂无数据",
    }.get(status, "暂无数据")
    return {
        "status": status,
        "label": label,
        "reason": reason,
        "usage_text": usage_text,
        "fee_text": fee_text,
    }


def _extract_top_business(result: AgentResult | None) -> dict[str, object]:
    """提取首推业务信息。

    Args:
        result: 智能体结果。

    Returns:
        首推业务展示结构。
    """

    if result is None or not result.recommended_policies:
        return {
            "title": "待生成",
            "category": "暂无",
            "price": "",
            "reason": "输入投诉后自动生成推荐业务。",
            "talking_point": "",
            "benefits": [],
            "risk_notes": [],
        }

    top_item = result.recommended_policies[0]
    policy = top_item.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    return {
        "title": str(top_item.get("title", policy.get("title", "待生成"))),
        "category": str(policy.get("category", "暂无")),
        "price": str(policy.get("price", "")),
        "reason": str(top_item.get("reason", "")),
        "talking_point": str(top_item.get("talking_point", "")),
        "benefits": _format_list_items(policy.get("benefits"), limit=4),
        "risk_notes": _format_list_items(policy.get("risk_notes"), limit=3),
    }


def _build_decision_summary(
    result: AgentResult | None,
    complaint: str,
    customer: dict[str, object] | None,
) -> dict[str, object]:
    """构建醒目的客户决策摘要。

    Args:
        result: 智能体结果。
        complaint: 客户投诉原文。
        customer: 本地客户画像。

    Returns:
        决策摘要字段。
    """

    analysis = result.customer_analysis if result is not None else {}
    risk_level = str(analysis.get("risk_level", "待生成"))
    complaint_type = str(analysis.get("complaint_type", "待生成"))
    emotion = str(analysis.get("emotion", "待生成"))
    priority = (
        _default_follow_priority(risk_level)
        if result is not None
        else "待生成"
    )
    overage = _derive_overage_status(complaint, customer, result)
    business = _extract_top_business(result)
    return {
        "overage": overage,
        "business": business,
        "risk_level": risk_level,
        "complaint_type": complaint_type,
        "emotion": emotion,
        "follow_priority": priority,
    }


def _render_decision_summary_panel(
    result: AgentResult | None,
    complaint: str,
    customer: dict[str, object] | None,
) -> None:
    """渲染客户分析结果中的关键信息摘要。

    Args:
        result: 智能体结果。
        complaint: 客户投诉原文。
        customer: 本地客户画像。

    Returns:
        无返回值。
    """

    summary = _build_decision_summary(result, complaint, customer)
    overage = summary["overage"]
    business = summary["business"]
    risk_level = str(summary["risk_level"])
    overage_status = str(overage.get("status", "未知"))
    cards = [
        {
            "label": "是否超耗",
            "value": str(overage.get("label", "暂无数据")),
            "desc": (
                f"{overage.get('usage_text', '')}｜"
                f"{overage.get('fee_text', '')}"
            ),
            "class": _overage_card_class(overage_status),
        },
        {
            "label": "推荐业务",
            "value": str(business.get("title", "待生成")),
            "desc": str(business.get("category", "暂无")),
            "class": "low" if result is not None else "",
        },
        {
            "label": "风险等级",
            "value": risk_level,
            "desc": "高风险客户需优先安抚" if risk_level == "高" else "用于安排跟进节奏",
            "class": _risk_card_class(risk_level),
        },
        {
            "label": "投诉类型",
            "value": str(summary["complaint_type"]),
            "desc": "用于匹配政策场景",
            "class": "",
        },
        {
            "label": "客户情绪",
            "value": str(summary["emotion"]),
            "desc": "辅助判断沟通语气",
            "class": "medium"
            if str(summary["emotion"]) in {"不满", "强烈不满", "焦虑"}
            else "",
        },
        {
            "label": "跟进优先级",
            "value": str(summary["follow_priority"]),
            "desc": "P1 需优先外呼或现场处理",
            "class": _risk_card_class(risk_level),
        },
    ]
    card_html = "".join(
        f"""
        <div class="decision-card {html.escape(card['class'])}">
            <div class="decision-label">{html.escape(card['label'])}</div>
            <div class="decision-value">{html.escape(card['value'])}</div>
            <div class="decision-desc">{html.escape(card['desc'])}</div>
        </div>
        """
        for card in cards
    )
    st.markdown(
        f"""
        <div class="decision-panel">
            <div class="section-title">客户决策摘要</div>
            <div class="decision-grid">{card_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_generation_status_bar(result: AgentResult) -> None:
    """渲染生成模式、模型和耗时信息。

    Args:
        result: 智能体结果。

    Returns:
        无返回值。
    """

    mode_text = "云端模型生成" if result.mode == "llm" else "本地模板兜底"
    cache_text = "命中缓存" if result.cached else "实时生成"
    mode_tone = "green" if result.mode == "llm" else "orange"
    status_html = f"""
    <div class="panel" style="padding: 12px 14px;">
        <div class="status-cluster" style="justify-content:flex-start;">
            {_badge(mode_text, mode_tone)}
            {_badge(result.model, "blue")}
            {_badge(f"{result.elapsed_seconds:.2f} 秒", "gray")}
            {_badge(cache_text, "gray")}
        </div>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)


def _render_top_business_card(result: AgentResult | None) -> None:
    """渲染首推业务大卡。

    Args:
        result: 智能体结果。

    Returns:
        无返回值。
    """

    business = _extract_top_business(result)
    benefit_chips = _render_chip_group(business.get("benefits", []), "chip-green")
    risk_chips = _render_chip_group(business.get("risk_notes", []), "chip-orange")
    st.markdown(
        f"""
        <div class="top-recommendation">
            <div style="display:flex;justify-content:space-between;gap:12px;">
                <span class="top-business-badge">首推业务</span>
                <span class="policy-rank">TOP 1</span>
            </div>
            <div class="top-business-title">
                {html.escape(str(business.get("title", "待生成")))}
            </div>
            <div class="policy-meta">
                {html.escape(str(business.get("category", "暂无")))}
                ｜ {html.escape(str(business.get("price", "")))}
            </div>
            <p><b>推荐理由：</b>{html.escape(str(business.get("reason", "")))}</p>
            <p><b>一句话卖点：</b>{html.escape(str(business.get("talking_point", "")))}</p>
            <div>{benefit_chips}</div>
            <div style="margin-top: 8px;">{risk_chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _overage_card_class(status: str) -> str:
    """根据超耗状态选择卡片样式。

    Args:
        status: 超耗状态。

    Returns:
        CSS 类名。
    """

    if status == "是":
        return "overage"
    if status == "疑似":
        return "medium"
    if status == "否":
        return "low"
    return ""


def _risk_card_class(risk_level: str) -> str:
    """根据风险等级选择卡片样式。

    Args:
        risk_level: 风险等级。

    Returns:
        CSS 类名。
    """

    score = _risk_score(risk_level)
    if score == 3:
        return "high"
    if score == 2:
        return "medium"
    if score == 1:
        return "low"
    return ""


def _render_chip_group(value: object, class_name: str = "chip-blue") -> str:
    """生成一组 HTML 标签。

    Args:
        value: 原始列表或文本。
        class_name: 附加 CSS 类。

    Returns:
        标签 HTML。
    """

    return "".join(
        f'<span class="chip {html.escape(class_name)}">{html.escape(item)}</span>'
        for item in _format_list_items(value)
    )


def _customer_value_level(
    customer: dict[str, object] | None = None,
) -> str:
    """判断客户价值等级。

    Args:
        customer: 本地客户画像。

    Returns:
        高价值、中价值或普通。
    """

    source = customer or _safe_get_current_customer() or {}
    monthly_fee = _as_float(source.get("monthly_fee"))
    tenure_years = _as_float(source.get("tenure_years"))
    if monthly_fee is None:
        monthly_fee = _as_float(st.session_state.get("monthly_fee_input")) or 0
    if tenure_years is None:
        tenure_years = _as_float(st.session_state.get("tenure_years_input")) or 0
    if monthly_fee >= 199 or tenure_years >= 5:
        return "高价值"
    if monthly_fee >= 99:
        return "中价值"
    return "普通"


def _customer_tags(
    customer: dict[str, object] | None = None,
    overage_status: dict[str, object] | None = None,
) -> list[str]:
    """生成客户标签，最多返回三个。

    Args:
        customer: 本地客户画像。
        overage_status: 超耗判断结果。

    Returns:
        客户标签列表。
    """

    source = customer or _safe_get_current_customer() or {}
    tags: list[str] = []
    if _customer_value_level(source) == "高价值":
        tags.append("高价值")
    wants_port_out = bool(
        source.get("wants_port_out", st.session_state.get("wants_port_out_input"))
    )
    if wants_port_out:
        tags.append("携转风险")
    if overage_status and overage_status.get("status") in {"是", "疑似"}:
        tags.append("流量超耗")
    family_count = _as_float(
        source.get("family_mobile_count", st.session_state.get("family_mobile_count_input"))
    )
    if family_count is not None and family_count >= 2:
        tags.append("家庭融合")
    has_broadband = bool(
        source.get("has_broadband", st.session_state.get("has_broadband_input"))
    )
    if has_broadband:
        tags.append("宽带用户")
    return tags[:3]


def _as_float(value: object) -> float | None:
    """把对象安全转换为浮点数。

    Args:
        value: 原始对象。

    Returns:
        可转换时返回浮点数，否则返回 None。
    """

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _render_customer_analysis_card(analysis: dict[str, object]) -> None:
    """渲染客户分析卡片。

    Args:
        analysis: 客户分析结构。

    Returns:
        无返回值。
    """

    key_needs = _format_list_items(analysis.get("key_needs"))
    chips = "".join(
        f'<span class="chip">{html.escape(item)}</span>' for item in key_needs
    )
    st.markdown(
        f"""
        <div class="analysis-card">
            <div class="section-title">客户分析</div>
            <div class="policy-meta">
                投诉类型：{html.escape(str(analysis.get("complaint_type", "其他")))}
                ｜ 情绪：{html.escape(str(analysis.get("emotion", "不满")))}
                ｜ 风险等级：{html.escape(str(analysis.get("risk_level", "中")))}
            </div>
            <div style="margin: 12px 0;">{chips}</div>
            <p>{html.escape(str(analysis.get("summary", "")))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recommended_policies(
    recommended_policies: list[dict[str, object]],
) -> None:
    """渲染推荐政策卡片。

    Args:
        recommended_policies: 推荐政策列表。

    Returns:
        无返回值。
    """

    st.markdown('<div class="section-title">推荐政策 Top 3</div>', unsafe_allow_html=True)
    if not recommended_policies:
        st.info("暂无推荐政策。")
        return
    columns = st.columns(min(3, len(recommended_policies)))
    for column, item in zip(columns, recommended_policies[:3], strict=False):
        with column:
            _render_policy_card(item)


def _render_policy_card(item: dict[str, object]) -> None:
    """渲染单张推荐政策卡。

    Args:
        item: 推荐政策视图。

    Returns:
        无返回值。
    """

    policy = item.get("policy", {})
    if not isinstance(policy, dict):
        policy = {}
    rank = int(item.get("rank", 1) or 1)
    title = str(item.get("title", policy.get("title", "未命名政策")))
    category = str(policy.get("category", "未分类"))
    price = str(policy.get("price", ""))
    local_score = str(item.get("local_score", 0))
    benefits = _format_list_items(policy.get("benefits"), limit=4)
    risks = _format_list_items(policy.get("risk_notes"), limit=2)
    benefit_chips = "".join(
        f'<span class="chip">{html.escape(benefit)}</span>'
        for benefit in benefits
    )
    risk_chips = "".join(
        f'<span class="chip">{html.escape(risk)}</span>' for risk in risks
    )
    st.markdown(
        f"""
        <div class="policy-card">
            <div class="policy-rank">TOP {rank}</div>
            <div class="policy-title">{html.escape(title)}</div>
            <div class="policy-meta">
                {html.escape(category)} ｜ {html.escape(price)}
                ｜ 本地匹配分 {html.escape(local_score)}
            </div>
            <p><b>推荐理由：</b>{html.escape(str(item.get("reason", "")))}</p>
            <p><b>一句话卖点：</b>{html.escape(str(item.get("talking_point", "")))}</p>
            <div>{benefit_chips}</div>
            <div style="margin-top: 8px;">{risk_chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f"查看办理条件与风险说明｜{title}"):
        st.write("适用场景：", str(policy.get("target", "")))
        _write_list("本地匹配原因", item.get("local_reasons", []))
        _write_list("办理条件", policy.get("conditions", []))
        _write_list("风险提醒", policy.get("risk_notes", []))


def _render_script_cards(script: dict[str, str]) -> None:
    """渲染四段式挽留话术。

    Args:
        script: 四段式话术。

    Returns:
        无返回值。
    """

    st.markdown('<div class="section-title">个性化挽留话术</div>', unsafe_allow_html=True)
    steps = []
    for index, (key, title) in enumerate(SCRIPT_SECTIONS, start=1):
        steps.append(
            f"""
            <div class="script-step">
                <div class="policy-rank">{index}</div>
                <b>{html.escape(title)}</b>
                <div class="muted-text">{html.escape(str(script.get(key, "")))}</div>
            </div>
            """
        )
    st.markdown(
        f'<div class="script-timeline">{"".join(steps)}</div>',
        unsafe_allow_html=True,
    )


def _render_note_cards(notes: list[str]) -> None:
    """渲染内部提醒卡片。

    Args:
        notes: 内部提醒列表。

    Returns:
        无返回值。
    """

    st.markdown('<div class="section-title">内部提醒</div>', unsafe_allow_html=True)
    if not notes:
        st.caption("暂无内部提醒。")
        return
    for note in notes:
        st.markdown(
            f"""
            <div class="note-card">
                <span>{html.escape(str(note))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_result_markdown(result: AgentResult) -> str:
    """构建可下载的 Markdown 方案。

    Args:
        result: 智能体输出。

    Returns:
        Markdown 文本。
    """

    analysis = result.customer_analysis
    mode_text = "云端模型生成" if result.mode == "llm" else "本地模板兜底"
    complaint = str(st.session_state.get("last_complaint_for_result", ""))
    customer = _safe_get_current_customer()
    decision = _build_decision_summary(result, complaint, customer)
    overage = decision["overage"]
    business = decision["business"]
    masked_phone = _mask_phone(_normalize_phone(st.session_state.get("phone_input", "")))
    lines = [
        "# 客户挽留方案",
        "",
        "## 生成信息",
        f"- 生成模式：{mode_text}",
        f"- 模型：{result.model}",
        f"- 耗时：{result.elapsed_seconds:.2f} 秒",
        f"- 是否命中缓存：{'是' if result.cached else '否'}",
        "",
        "## 客户决策摘要",
        f"- 手机号：{masked_phone}",
        f"- 是否超耗：{overage.get('label', '暂无数据')}",
        f"- 推荐业务：{business.get('title', '待生成')}",
        f"- 风险等级：{decision.get('risk_level', '中')}",
        f"- 投诉类型：{decision.get('complaint_type', '其他')}",
        f"- 跟进优先级：{decision.get('follow_priority', 'P2')}",
        "",
        "## 客户分析",
        f"- 投诉类型：{analysis.get('complaint_type', '其他')}",
        f"- 情绪：{analysis.get('emotion', '不满')}",
        f"- 风险等级：{analysis.get('risk_level', '中')}",
        f"- 关键诉求：{'、'.join(_format_list_items(analysis.get('key_needs')))}",
        f"- 摘要：{analysis.get('summary', '')}",
        "",
        "## 推荐政策 Top 3",
    ]
    for item in result.recommended_policies[:3]:
        policy = item.get("policy", {})
        if not isinstance(policy, dict):
            policy = {}
        lines.extend(
            [
                "",
                f"### TOP {item.get('rank', '')}｜{item.get('title', '')}",
                f"- 分类：{policy.get('category', '')}",
                f"- 价格：{policy.get('price', '')}",
                f"- 本地匹配分：{item.get('local_score', '')}",
                f"- 推荐理由：{item.get('reason', '')}",
                f"- 一句话卖点：{item.get('talking_point', '')}",
                f"- 核心权益：{'、'.join(_format_list_items(policy.get('benefits'), 4))}",
                f"- 风险提醒：{'、'.join(_format_list_items(policy.get('risk_notes'), 2))}",
            ]
        )
    lines.extend(["", "## 四段式话术", _build_full_script_text(result.retention_script)])
    lines.extend(["", "## 内部提醒"])
    for note in result.internal_notes:
        lines.append(f"- {note}")
    if result.llm_error:
        lines.extend(["", "## 失败原因", result.llm_error])
    return "\n".join(str(line) for line in lines)


def _render_dashboard_page() -> None:
    """渲染后台客户风险看板页面。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    sorted_history = _get_sorted_history()
    total_cases = int(st.session_state["total_cases"])
    average_elapsed = (
        float(st.session_state["elapsed_total"]) / total_cases
        if total_cases
        else 0.0
    )
    high_risk_percent = (
        int(st.session_state["high_risk_cases"]) / total_cases * 100
        if total_cases
        else 0.0
    )
    priority_wait_count = sum(
        1 for row in sorted_history if row.get("处理状态") == "待优先跟进"
    )
    kpi_html = "".join(
        [
            _metric_card("本次处理", total_cases, "当前会话记录", "neutral"),
            _metric_card("高风险客户", st.session_state["high_risk_cases"], "默认排在队列前列", "danger"),
            _metric_card("高风险占比", f"{high_risk_percent:.1f}%", "用于经理快速判断压力", "warning"),
            _metric_card("待优先跟进", priority_wait_count, "处理状态为待优先跟进", "danger"),
            _metric_card("云端生成次数", st.session_state["llm_success_count"], "LLM 核心链路", "success"),
            _metric_card("平均耗时", f"{average_elapsed:.2f} 秒", "本次演示平均", "neutral"),
        ]
    )
    _section_header("后台客户风险看板", "按风险、超耗、携转意向组织客户跟进队列。")
    st.markdown(f'<div class="decision-kpi-grid">{kpi_html}</div>', unsafe_allow_html=True)
    _render_high_risk_cards(sorted_history)

    if not sorted_history:
        _empty_state("暂无风险队列", "完成一次客户挽留方案生成后，这里会出现待跟进客户。")
        return

    _section_header("客户风险队列", "默认高风险在前，可按风险、投诉类型、状态和手机号后四位筛选。")
    risk_col, type_col, phone_col, status_col = st.columns(4)
    with risk_col:
        risk_filter = st.selectbox("风险等级", ["全部", "高", "中", "低"])
    complaint_types = sorted(
        {
            str(row.get("投诉类型", "其他"))
            for row in sorted_history
            if row.get("投诉类型")
        }
    )
    with type_col:
        complaint_type_filter = st.selectbox("投诉类型", ["全部"] + complaint_types)
    with phone_col:
        phone_query = st.text_input("手机号后四位", placeholder="例如 8001")
    statuses = sorted(
        {
            str(row.get("处理状态", ""))
            for row in sorted_history
            if row.get("处理状态")
        }
    )
    with status_col:
        status_filter = st.selectbox("处理状态", ["全部"] + statuses)

    filtered_history = _filter_history(
        sorted_history,
        risk_filter=risk_filter,
        complaint_type_filter=complaint_type_filter,
        phone_query=phone_query,
    )
    if status_filter != "全部":
        filtered_history = [
            row for row in filtered_history if row.get("处理状态") == status_filter
        ]

    st.markdown('<div class="risk-queue-card">', unsafe_allow_html=True)
    display_rows = _visible_history_rows(filtered_history)
    if display_rows:
        st.dataframe(display_rows, width="stretch", hide_index=True)
    else:
        st.caption("当前筛选条件下暂无客户记录。")
    export_col, clear_col = st.columns([0.62, 0.38])
    with export_col:
        st.download_button(
            "导出客户风险队列 CSV",
            data=_to_csv_bytes(filtered_history),
            file_name="client_savior_risk_queue.csv",
            mime="text/csv",
            width="stretch",
        )
    with clear_col:
        confirm_clear = st.checkbox("确认清空本次演示记录")
        if confirm_clear and st.button("清空本次看板记录", width="stretch"):
            _reset_dashboard_state()
            st.success("已清空本次演示看板记录。")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_dashboard_tab() -> None:
    """渲染后台客户风险看板。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.markdown(
        '<div class="section-title">后台客户风险看板</div>',
        unsafe_allow_html=True,
    )
    total_cases = int(st.session_state["total_cases"])
    average_elapsed = (
        float(st.session_state["elapsed_total"]) / total_cases
        if total_cases
        else 0.0
    )
    sorted_history = _get_sorted_history()
    high_risk_percent = (
        int(st.session_state["high_risk_cases"]) / total_cases * 100
        if total_cases
        else 0.0
    )
    priority_wait_count = sum(
        1 for row in sorted_history if row.get("处理状态") == "待优先跟进"
    )
    port_out_count = sum(1 for row in sorted_history if row.get("明确携转") == "是")

    col_total, col_high, col_llm, col_fallback, col_elapsed = st.columns(5)
    col_total.metric("已处理投诉数", total_cases)
    col_high.metric("高风险客户数", st.session_state["high_risk_cases"])
    col_llm.metric("云端模型生成次数", st.session_state["llm_success_count"])
    col_fallback.metric("本地模板兜底次数", st.session_state["fallback_count"])
    col_elapsed.metric("平均耗时", f"{average_elapsed:.2f} 秒")

    col_ratio, col_wait, col_port, col_today = st.columns(4)
    col_ratio.metric("高风险占比", f"{high_risk_percent:.1f}%")
    col_wait.metric("待优先跟进数", priority_wait_count)
    col_port.metric("有携转意向客户数", port_out_count)
    col_today.metric("本次演示记录数", total_cases)

    st.markdown(
        '<div class="flow-card">输入投诉 → 政策召回 → 模型生成 → 一线执行</div>',
        unsafe_allow_html=True,
    )

    _render_high_risk_cards(sorted_history)

    col_left, col_right = st.columns(2)
    with col_left:
        _render_counter_chart("投诉类型分布", st.session_state["complaint_type_counter"])
    with col_right:
        top_policies = _top_items(st.session_state["policy_counter"], limit=5)
        _render_counter_chart("推荐业务次数 Top 5", top_policies)

    if sorted_history:
        st.subheader("客户风险队列")
        risk_filter_col, type_filter_col, phone_filter_col = st.columns(3)
        with risk_filter_col:
            risk_filter = st.selectbox(
                "风险等级筛选",
                ["全部", "高", "中", "低"],
            )
        complaint_types = sorted(
            {
                str(row.get("投诉类型", "其他"))
                for row in sorted_history
                if row.get("投诉类型")
            }
        )
        with type_filter_col:
            complaint_type_filter = st.selectbox(
                "投诉类型筛选",
                ["全部"] + complaint_types,
            )
        with phone_filter_col:
            phone_query = st.text_input(
                "手机号搜索",
                placeholder="支持后四位或完整手机号",
            )

        filtered_history = _filter_history(
            sorted_history,
            risk_filter=risk_filter,
            complaint_type_filter=complaint_type_filter,
            phone_query=phone_query,
        )
        display_rows = _visible_history_rows(filtered_history)
        if display_rows:
            st.dataframe(display_rows, width="stretch", hide_index=True)
        else:
            st.caption("当前筛选条件下暂无客户记录。")
        st.download_button(
            "导出客户风险队列 CSV",
            data=_to_csv_bytes(filtered_history),
            file_name="client_savior_risk_queue.csv",
            mime="text/csv",
            width="stretch",
        )
    else:
        st.info("暂无处理记录。")

    st.divider()
    confirm_clear = st.checkbox("确认清空本次演示记录")
    if confirm_clear and st.button("清空本次看板记录"):
        _reset_dashboard_state()
        st.success("已清空本次演示看板记录。")
        st.rerun()


def _update_dashboard(
    result: AgentResult,
    phone: str = "",
    masked_phone: str = "未填写",
    complaint: str = "",
) -> None:
    """更新本次演示看板数据。

    Args:
        result: 智能体输出。
        phone: 标准化后的手机号，仅用于本地演示看板记录。
        masked_phone: 页面展示使用的脱敏手机号。
        complaint: 客户投诉原文摘要来源。

    Returns:
        无返回值。
    """

    st.session_state["total_cases"] += 1
    st.session_state["elapsed_total"] += result.elapsed_seconds
    if result.mode == "llm":
        st.session_state["llm_success_count"] += 1
    else:
        st.session_state["fallback_count"] += 1

    analysis = result.customer_analysis
    risk_level = str(analysis.get("risk_level", ""))
    if risk_level == "高":
        st.session_state["high_risk_cases"] += 1

    complaint_type = str(analysis.get("complaint_type", "其他"))
    emotion = str(analysis.get("emotion", "不满"))
    key_needs_text = _format_key_needs(analysis.get("key_needs"))
    _increase_counter("complaint_type_counter", complaint_type)
    for policy in result.recommended_policies:
        title = str(policy.get("title", policy.get("policy_id", "未知政策")))
        _increase_counter("policy_counter", title)
    current_customer = _safe_get_current_customer()
    overage_status = _derive_overage_status(complaint, current_customer, result)
    top_business = _extract_top_business(result)
    top_business_title = str(top_business.get("title", ""))
    customer_value = _customer_value_level(current_customer)
    customer_tags = "、".join(_customer_tags(current_customer, overage_status))
    risk_sort_value = _risk_score(risk_level)

    st.session_state["history"].append(
        {
            "序号": st.session_state["total_cases"],
            "生成时间": datetime.now().strftime("%H:%M:%S"),
            "手机号": masked_phone,
            "_raw_phone": phone,
            "投诉类型": complaint_type,
            "风险等级": risk_level,
            "风险排序": risk_sort_value,
            "客户情绪": emotion,
            "关键诉求": key_needs_text,
            "是否超耗": overage_status.get("label", "暂无数据"),
            "推荐业务": top_business_title,
            "客户价值": customer_value,
            "客户标签": customer_tags,
            "当前月租": st.session_state["monthly_fee_input"],
            "客户类型": st.session_state["customer_type_input"],
            "明确携转": "是" if st.session_state["wants_port_out_input"] else "否",
            "推荐政策 Top 1": top_business_title,
            "处理状态": _default_follow_status(risk_level),
            "跟进优先级": _default_follow_priority(risk_level),
            "模式": "云端模型生成" if result.mode == "llm" else "本地模板兜底",
            "耗时": round(result.elapsed_seconds, 2),
            "投诉摘要": complaint[:60],
        }
    )


def _increase_counter(counter_key: str, item_key: str) -> None:
    """更新 session_state 中的计数字典。

    Args:
        counter_key: 计数字典的状态键。
        item_key: 需要增加计数的项目。

    Returns:
        无返回值。
    """

    counter = dict(st.session_state[counter_key])
    counter[item_key] = counter.get(item_key, 0) + 1
    st.session_state[counter_key] = counter


def _normalize_phone(raw_phone: object) -> str:
    """标准化手机号，仅用于本地演示看板记录。

    Args:
        raw_phone: 用户输入的手机号。

    Returns:
        去除空格和短横线后的手机号字符串。
    """

    if raw_phone is None:
        return ""
    return str(raw_phone).replace(" ", "").replace("-", "").strip()


def _mask_phone(phone: str) -> str:
    """脱敏手机号，避免页面和导出暴露完整号码。

    Args:
        phone: 标准化后的手机号。

    Returns:
        脱敏后的手机号展示文本。
    """

    if not phone:
        return "未填写"
    if phone.isdigit() and len(phone) == 11:
        return f"{phone[:3]}****{phone[-4:]}"
    return f"{phone[:3]}****"


def _risk_score(risk_level: str) -> int:
    """把风险等级转换为排序分。

    Args:
        risk_level: 风险等级文本。

    Returns:
        风险排序分，高风险最大。
    """

    mapping = {"高": 3, "中": 2, "低": 1}
    text = str(risk_level).strip()
    if text in mapping:
        return mapping[text]
    for key, score in mapping.items():
        if key in text:
            return score
    return 0


def _default_follow_status(risk_level: str) -> str:
    """根据风险等级给出默认处理状态。

    Args:
        risk_level: 风险等级文本。

    Returns:
        默认处理状态。
    """

    score = _risk_score(risk_level)
    if score == 3:
        return "待优先跟进"
    if score == 2:
        return "待跟进"
    return "已生成方案"


def _default_follow_priority(risk_level: str) -> str:
    """根据风险等级给出默认跟进优先级。

    Args:
        risk_level: 风险等级文本。

    Returns:
        默认跟进优先级。
    """

    score = _risk_score(risk_level)
    if score == 3:
        return "P1"
    if score == 2:
        return "P2"
    return "P3"


def _format_key_needs(value: object) -> str:
    """格式化关键诉求字段。

    Args:
        value: 原始关键诉求字段。

    Returns:
        用顿号连接的诉求文本。
    """

    return "、".join(_format_list_items(value))


def _get_sorted_history() -> list[dict[str, object]]:
    """获取按风险排序后的历史记录。

    Args:
        无参数。

    Returns:
        风险优先、同风险新记录优先的历史记录副本。
    """

    rows = [dict(row) for row in st.session_state.get("history", [])]
    return sorted(rows, key=_history_sort_key, reverse=True)


def _history_sort_key(row: dict[str, object]) -> tuple[int, int]:
    """构造客户风险队列排序键。

    Args:
        row: 单条历史记录。

    Returns:
        风险排序分和序号组成的排序键。
    """

    risk_value = row.get("风险排序")
    try:
        risk_sort = int(risk_value)
    except (TypeError, ValueError):
        risk_sort = _risk_score(str(row.get("风险等级", "")))
    try:
        sequence = int(row.get("序号", 0))
    except (TypeError, ValueError):
        sequence = 0
    return risk_sort, sequence


def _filter_history(
    rows: list[dict[str, object]],
    risk_filter: str,
    complaint_type_filter: str,
    phone_query: str,
) -> list[dict[str, object]]:
    """筛选客户风险队列。

    Args:
        rows: 已排序的历史记录。
        risk_filter: 风险等级筛选值。
        complaint_type_filter: 投诉类型筛选值。
        phone_query: 手机号搜索词。

    Returns:
        筛选后的历史记录。
    """

    normalized_query = _normalize_phone(phone_query)
    query_text = str(phone_query).strip().casefold()
    filtered_rows = []
    for row in rows:
        if risk_filter != "全部" and row.get("风险等级") != risk_filter:
            continue
        if (
            complaint_type_filter != "全部"
            and row.get("投诉类型") != complaint_type_filter
        ):
            continue
        if normalized_query or query_text:
            masked_phone = str(row.get("手机号", "")).casefold()
            raw_phone = str(row.get("_raw_phone", "")).casefold()
            normalized_raw = _normalize_phone(raw_phone).casefold()
            if not (
                (normalized_query and normalized_query in normalized_raw)
                or (normalized_query and normalized_query in masked_phone)
                or query_text in masked_phone
                or query_text in raw_phone
            ):
                continue
        filtered_rows.append(row)
    return filtered_rows


def _visible_history_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """移除内部列，生成页面表格行。

    Args:
        rows: 原始历史记录。

    Returns:
        仅包含可展示字段的行。
    """

    return [
        {column: row.get(column, "") for column in HISTORY_VISIBLE_COLUMNS}
        for row in rows
    ]


def _to_csv_bytes(rows: list[dict[str, object]]) -> bytes:
    """把当前筛选记录导出为 UTF-8 with BOM CSV。

    Args:
        rows: 当前筛选后的历史记录。

    Returns:
        CSV 字节内容，不包含完整手机号和内部排序列。
    """

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=HISTORY_VISIBLE_COLUMNS)
    writer.writeheader()
    for row in _visible_history_rows(rows):
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


def _render_high_risk_cards(rows: list[dict[str, object]]) -> None:
    """渲染高风险客户优先跟进卡片。

    Args:
        rows: 已排序的历史记录。

    Returns:
        无返回值。
    """

    _section_header("高风险客户优先跟进", "最多展示 3 条 P1 风险客户，便于现场经理安排跟进。")
    high_risk_rows = [
        row for row in rows if str(row.get("风险等级", "")) == "高"
    ][:3]
    if not high_risk_rows:
        st.caption("暂无高风险客户。")
        return

    columns = st.columns(len(high_risk_rows))
    for column, row in zip(columns, high_risk_rows, strict=False):
        with column:
            summary = str(row.get("投诉摘要", ""))[:40]
            st.markdown(
                f"""
                <div class="risk-client-card">
                    <b>{html.escape(str(row.get("手机号", "未填写")))}</b>
                    <div class="policy-meta">
                        风险等级：{html.escape(str(row.get("风险等级", "")))}
                        ｜ {html.escape(str(row.get("跟进优先级", "")))}
                    </div>
                    <div class="policy-meta">
                        投诉类型：{html.escape(str(row.get("投诉类型", "")))}
                    </div>
                    <div class="policy-meta">
                        状态：{html.escape(str(row.get("处理状态", "")))}
                    </div>
                    <div class="policy-meta">
                        是否超耗：{html.escape(str(row.get("是否超耗", "")))}
                    </div>
                    <p>推荐业务：{html.escape(str(row.get("推荐业务", "")))}</p>
                    <p>投诉摘要：{html.escape(summary)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _reset_dashboard_state() -> None:
    """清空本次演示看板记录。

    Args:
        无参数。

    Returns:
        无返回值。
    """

    st.session_state["total_cases"] = 0
    st.session_state["high_risk_cases"] = 0
    st.session_state["llm_success_count"] = 0
    st.session_state["fallback_count"] = 0
    st.session_state["elapsed_total"] = 0.0
    st.session_state["complaint_type_counter"] = {}
    st.session_state["policy_counter"] = {}
    st.session_state["history"] = []
    st.session_state["last_result"] = None


def _render_counter_chart(title: str, counter: dict[str, int]) -> None:
    """渲染计数柱状图。

    Args:
        title: 图表标题。
        counter: 计数字典。

    Returns:
        无返回值。
    """

    st.write(title)
    rows = [{"项目": key, "数量": value} for key, value in counter.items()]
    if rows:
        st.bar_chart(rows, x="项目", y="数量")
    else:
        st.caption("暂无数据。")


def _render_policy_library_page(policies: list[dict[str, object]]) -> None:
    """渲染政策货架页面。

    Args:
        policies: 政策卡列表。

    Returns:
        无返回值。
    """

    categories = sorted({str(policy.get("category", "")) for policy in policies})
    quick_categories = [
        "全部",
        "大流量卡",
        "家庭融合",
        "无忧包",
        "升档",
        "亲情网",
        "宽带/FTTR",
        "终端",
        "商客融合",
    ]
    category_options = ["全部"] + sorted(set(categories + quick_categories[1:]))
    if st.session_state["policy_category_filter"] not in category_options:
        st.session_state["policy_category_filter"] = "全部"

    _section_header("政策货架", "按业务分类快速检索政策，主信息直接展示，细节再展开。")
    search_col, category_col, count_col = st.columns([0.52, 0.28, 0.20])
    with search_col:
        query = st.text_input(
            "搜索政策",
            placeholder="输入政策名、关键词或适用场景",
            key="policy_query",
        )
    with category_col:
        selected_category = st.selectbox(
            "分类筛选",
            category_options,
            key="policy_category_filter",
        )
    with count_col:
        st.metric("总政策数", len(policies))

    shortcut_columns = st.columns(5)
    for index, category in enumerate(quick_categories):
        with shortcut_columns[index % len(shortcut_columns)]:
            st.button(
                category,
                key=f"policy_shelf_category_{index}",
                width="stretch",
                on_click=_set_policy_category,
                args=(category,),
            )

    filtered_policies = [
        policy
        for policy in policies
        if _policy_visible(policy, query, selected_category)
    ]
    st.caption(f"当前筛选结果：{len(filtered_policies)} 条")
    for row_start in range(0, len(filtered_policies), 3):
        columns = st.columns(3)
        for column, policy in zip(columns, filtered_policies[row_start : row_start + 3], strict=False):
            with column:
                _render_policy_library_card(policy)


def _render_policy_tab(policies: list[dict[str, object]]) -> None:
    """渲染政策库。

    Args:
        policies: 政策卡列表。

    Returns:
        无返回值。
    """

    st.markdown('<div class="section-title">政策库</div>', unsafe_allow_html=True)
    categories = sorted({str(policy.get("category", "")) for policy in policies})
    if st.session_state["policy_category_filter"] not in ["全部"] + categories:
        st.session_state["policy_category_filter"] = "全部"

    st.caption("分类快捷筛选")
    shortcut_columns = st.columns(4)
    quick_categories = ["全部"] + categories[:7]
    for index, category in enumerate(quick_categories):
        with shortcut_columns[index % 4]:
            st.button(
                category or "未分类",
                key=f"policy_category_button_{index}",
                width="stretch",
                on_click=_set_policy_category,
                args=(category,),
            )

    col_search, col_category = st.columns([2, 1])
    with col_search:
        query = st.text_input(
            "搜索政策",
            placeholder="输入政策名、关键词或适用场景",
            key="policy_query",
        )
    with col_category:
        selected_category = st.selectbox(
            "分类筛选",
            ["全部"] + categories,
            key="policy_category_filter",
        )

    filtered_policies = [
        policy
        for policy in policies
        if _policy_visible(policy, query, selected_category)
    ]
    stat_total, stat_category, stat_filtered = st.columns(3)
    stat_total.metric("政策卡数量", len(policies))
    stat_category.metric("分类数量", len(categories))
    stat_filtered.metric("当前筛选结果", len(filtered_policies))

    for policy in filtered_policies:
        _render_policy_library_card(policy)


def _set_policy_category(category: str) -> None:
    """设置政策库分类筛选。

    Args:
        category: 目标分类。

    Returns:
        无返回值。
    """

    st.session_state["policy_category_filter"] = category


def _render_policy_library_card(policy: dict[str, object]) -> None:
    """渲染政策库中的单张政策卡。

    Args:
        policy: 单张政策卡。

    Returns:
        无返回值。
    """

    benefits = _format_list_items(policy.get("benefits"), limit=4)
    conditions = _format_list_items(policy.get("conditions"), limit=2)
    risks = _format_list_items(policy.get("risk_notes"), limit=2)
    benefit_chips = "".join(_chip(benefit, "blue") for benefit in benefits)
    st.markdown(
        f"""
        <div class="library-card">
            <div class="policy-meta">
                {html.escape(str(policy.get("id", "")))}
                · {html.escape(str(policy.get("category", "未分类")))}
            </div>
            <div class="policy-title">
                {html.escape(str(policy.get("title", "未命名政策")))}
            </div>
            <div class="policy-meta">
                价格：{html.escape(str(policy.get("price", "")))}
            </div>
            <p>目标客户：{html.escape(str(policy.get("target", "")))}</p>
            <div>{benefit_chips}</div>
            <p><b>办理条件：</b>{html.escape("；".join(conditions))}</p>
            <p><b>风险提醒：</b>{html.escape("；".join(risks))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander(f"查看详情｜{policy.get('id', '')}"):
        _write_list("关键词", policy.get("keywords", []))
        _write_list("办理条件", policy.get("conditions", []))
        _write_list("风险提醒", policy.get("risk_notes", []))
        st.write("话术提示：", str(policy.get("script_hint", "")))


def _policy_visible(
    policy: dict[str, object],
    query: str,
    selected_category: str,
) -> bool:
    """判断政策卡是否满足筛选条件。

    Args:
        policy: 单张政策卡。
        query: 搜索词。
        selected_category: 选中的分类。

    Returns:
        满足筛选条件时返回 True。
    """

    if selected_category != "全部" and not _policy_category_match(
        str(policy.get("category", "")),
        selected_category,
    ):
        return False
    if not query:
        return True
    search_text = json.dumps(policy, ensure_ascii=False).casefold()
    return query.casefold() in search_text


def _policy_category_match(policy_category: str, selected_category: str) -> bool:
    """判断政策分类是否匹配筛选项。

    Args:
        policy_category: 政策原始分类。
        selected_category: 页面筛选分类。

    Returns:
        匹配时返回 True。
    """

    alias_mapping = {
        "无忧包": {"高套保有"},
        "升档": {"低档升档", "升档扩容"},
        "亲情网": {"家庭黏性"},
        "宽带/FTTR": {"宽带组网", "重点客群宽带"},
        "终端": {"终端换机"},
    }
    if policy_category == selected_category:
        return True
    return policy_category in alias_mapping.get(selected_category, set())


def _write_list(title: str, value: object) -> None:
    """渲染列表字段。

    Args:
        title: 字段标题。
        value: 字段值。

    Returns:
        无返回值。
    """

    items = _format_list_items(value)
    if not items:
        st.write(f"{title}：无")
        return
    st.write(f"{title}：")
    for item in items:
        st.markdown(f"- {item}")


def _format_list_items(value: object, limit: int | None = None) -> list[str]:
    """把任意字段规范为字符串列表。

    Args:
        value: 原始字段值。
        limit: 最大返回数量。

    Returns:
        字符串列表。
    """

    if value is None:
        items: list[object] = []
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    formatted = [str(item) for item in items if str(item).strip()]
    if limit is not None:
        return formatted[:limit]
    return formatted


def _build_full_script_text(script: dict[str, str]) -> str:
    """拼接四段式话术文本。

    Args:
        script: 四段式话术。

    Returns:
        可下载方案中使用的话术文本。
    """

    return "\n\n".join(
        f"【{title}】{script.get(key, '')}" for key, title in SCRIPT_SECTIONS
    )


def _risk_kind(risk_level: str) -> str:
    """把风险等级映射为样式类型。

    Args:
        risk_level: 风险等级文本。

    Returns:
        样式类型。
    """

    if "高" in risk_level:
        return "high"
    if "低" in risk_level:
        return "low"
    return "medium"


def _top_items(counter: dict[str, int], limit: int) -> dict[str, int]:
    """取计数字典前若干项。

    Args:
        counter: 计数字典。
        limit: 返回数量。

    Returns:
        截断后的计数字典。
    """

    return dict(sorted(counter.items(), key=lambda item: item[1], reverse=True)[:limit])


if __name__ == "__main__":
    main()
