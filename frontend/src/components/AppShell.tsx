import { ApiOutlined } from "@ant-design/icons";
import { Button, Layout, Menu, message } from "antd";
import type { MenuProps } from "antd";
import type { ReactNode } from "react";
import { getErrorMessage, testLLM } from "../api/client";
import type { AppConfig, DashboardMetrics } from "../api/types";
import StatusPill from "./StatusPill";

type AppShellProps = {
  activePage: string;
  config: AppConfig | null;
  metrics: DashboardMetrics | null;
  children: ReactNode;
  onPageChange: (page: string) => void;
};

const items: MenuProps["items"] = [
  { key: "workbench", label: "客服工作台" },
  { key: "dashboard", label: "风险看板" },
  { key: "policies", label: "政策库" }
];

export default function AppShell({
  activePage,
  config,
  metrics,
  children,
  onPageChange
}: AppShellProps) {
  const handleTestLLM = async () => {
    try {
      const response = await testLLM();
      if (response.ok) {
        message.success(`LLM 连通正常，耗时 ${response.elapsed_seconds} 秒`);
      } else {
        message.error(`失败原因：${response.error}`);
      }
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  return (
    <Layout className="app-shell">
      <header className="app-header">
        <div className="brand-row">
          <div className="brand-title">客户拯救者</div>
          <span className="brand-divider">/</span>
          <div className="brand-subtitle">The Client Savior</div>
          <p>投诉秒变留人机会，政策套餐自动配对</p>
        </div>
      </header>
      <nav className="nav-shell">
        <Menu
          mode="horizontal"
          selectedKeys={[activePage]}
          items={items}
          onClick={(event) => onPageChange(event.key)}
        />
      </nav>
      <div className="shell-body">
        <main className="main-shell">{children}</main>
        <aside className="side-status" aria-label="运行状态侧边栏">
          <div className="side-panel">
            <div className="side-title">运行状态</div>
            <p className="side-subtitle">模型与本次演示统计</p>
            <div className="status-cluster">
              <StatusPill
                label="云端模型"
                value={config?.llm_configured ? "已配置" : "未配置"}
                tone={config?.llm_configured ? "green" : "orange"}
              />
              <StatusPill label="模型" value={config?.model || "-"} tone="blue" />
              <StatusPill
                label="本次处理"
                value={metrics?.total_cases || 0}
                tone="gray"
              />
              <StatusPill
                label="高风险"
                value={metrics?.high_risk_cases || 0}
                tone="red"
              />
            </div>
            <Button
              block
              className="side-test-button"
              icon={<ApiOutlined />}
              onClick={handleTestLLM}
            >
              LLM 连通性测试
            </Button>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
