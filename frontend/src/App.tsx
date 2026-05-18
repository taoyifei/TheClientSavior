import { message, Spin } from "antd";
import { useCallback, useEffect, useState } from "react";
import {
  getConfig,
  getDashboard,
  getDemoCases,
  getErrorMessage,
  getPolicies
} from "./api/client";
import type {
  AppConfig,
  DashboardResponse,
  DemoCase,
  Policy
} from "./api/types";
import AppShell from "./components/AppShell";
import DashboardPage from "./pages/DashboardPage";
import PolicyPage from "./pages/PolicyPage";
import WorkbenchPage from "./pages/WorkbenchPage";

export default function App() {
  const [activePage, setActivePage] = useState("workbench");
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [demoCases, setDemoCases] = useState<DemoCase[]>([]);
  const [loading, setLoading] = useState(true);

  const reloadDashboard = useCallback(async () => {
    const nextDashboard = await getDashboard();
    setDashboard(nextDashboard);
  }, []);

  useEffect(() => {
    async function bootstrap() {
      try {
        const [nextConfig, nextDashboard, nextPolicies, nextDemoCases] =
          await Promise.all([
            getConfig(),
            getDashboard(),
            getPolicies(),
            getDemoCases()
          ]);
        setConfig(nextConfig);
        setDashboard(nextDashboard);
        setPolicies(nextPolicies);
        setDemoCases(nextDemoCases);
      } catch (error) {
        message.error(getErrorMessage(error));
      } finally {
        setLoading(false);
      }
    }
    bootstrap();
  }, []);

  if (loading) {
    return (
      <div className="boot-screen">
        <Spin size="large" />
        <span>正在连接客户拯救者后端...</span>
      </div>
    );
  }

  return (
    <AppShell
      activePage={activePage}
      config={config}
      metrics={dashboard?.metrics || null}
      onPageChange={setActivePage}
    >
      <div
        className={`page-keepalive ${activePage === "workbench" ? "active" : ""}`}
        aria-hidden={activePage !== "workbench"}
      >
        <WorkbenchPage
          demoCases={demoCases}
          onDashboardChanged={reloadDashboard}
        />
      </div>
      <div
        className={`page-keepalive ${activePage === "dashboard" ? "active" : ""}`}
        aria-hidden={activePage !== "dashboard"}
      >
        <DashboardPage
          dashboard={dashboard}
          onDashboardChanged={reloadDashboard}
        />
      </div>
      <div
        className={`page-keepalive ${activePage === "policies" ? "active" : ""}`}
        aria-hidden={activePage !== "policies"}
      >
        <PolicyPage policies={policies} />
      </div>
    </AppShell>
  );
}
