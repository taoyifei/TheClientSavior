import { Button, Checkbox, message, Popconfirm } from "antd";
import { useState } from "react";
import { getErrorMessage, resetDashboard } from "../api/client";
import type { DashboardResponse } from "../api/types";
import EmptyState from "../components/EmptyState";
import RiskQueueTable from "../components/RiskQueueTable";

type DashboardPageProps = {
  dashboard: DashboardResponse | null;
  onDashboardChanged: () => Promise<void>;
};

export default function DashboardPage({
  dashboard,
  onDashboardChanged
}: DashboardPageProps) {
  const [confirmed, setConfirmed] = useState(false);
  const metrics = dashboard?.metrics;
  const rows = dashboard?.risk_queue || [];
  const highRiskRows = rows.filter((row) => row.risk_level === "高").slice(0, 3);

  const handleReset = async () => {
    try {
      await resetDashboard();
      await onDashboardChanged();
      setConfirmed(false);
      message.success("已清空本次演示看板记录。");
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  return (
    <div className="dashboard-page">
      <div className="dashboard-metric-shell">
        <section className="metric-group">
          <div className="metric-group-title">处理效率</div>
          <div className="metric-grid compact">
            <div className="metric-card">
              <span>本次处理</span>
              <strong>{metrics?.total_cases || 0}</strong>
            </div>
            <div className="metric-card success">
              <span>云端生成次数</span>
              <strong>{metrics?.llm_success_count || 0}</strong>
            </div>
            <div className="metric-card">
              <span>平均耗时</span>
              <strong>{(metrics?.average_elapsed || 0).toFixed(2)} 秒</strong>
            </div>
          </div>
        </section>
        <section className="metric-group risk">
          <div className="metric-group-title">风险队列</div>
          <div className="metric-grid compact">
            <div className="metric-card danger">
              <span>高风险客户</span>
              <strong>{metrics?.high_risk_cases || 0}</strong>
            </div>
            <div className="metric-card warning">
              <span>高风险占比</span>
              <strong>{(metrics?.high_risk_percent || 0).toFixed(1)}%</strong>
            </div>
            <div className="metric-card danger">
              <span>待优先跟进</span>
              <strong>{metrics?.priority_wait_count || 0}</strong>
            </div>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>高风险客户优先跟进</h3>
            <p>展示最近风险最高的客户，便于现场经理快速安排跟进。</p>
          </div>
        </div>
        {highRiskRows.length ? (
          <div className="risk-card-grid">
            {highRiskRows.map((row) => (
              <article className="risk-queue-card" key={String(row.sequence)}>
                <div className="risk-card-head">
                  <strong>{row.phone_masked}</strong>
                  <span className="chip red">{row.risk_level}</span>
                </div>
                <p>
                  {row.complaint_type} · {row.overage_label}
                </p>
                <p>首推：{row.top_business}</p>
                <div className="risk-action-line">
                  <span>{row.follow_priority}</span>
                  <strong>{row.status || "建议回呼"}</strong>
                </div>
                <small>{row.complaint_summary}</small>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            title="暂无高风险客户"
            body="生成方案后，高风险客户会优先出现在这里。"
          />
        )}
      </section>

      <RiskQueueTable rows={rows} />

      <section className="panel clear-panel">
        <Checkbox
          checked={confirmed}
          onChange={(event) => setConfirmed(event.target.checked)}
        >
          确认清空本次演示记录
        </Checkbox>
        <Popconfirm
          title="确认清空看板记录？"
          okText="清空"
          cancelText="取消"
          disabled={!confirmed}
          onConfirm={handleReset}
        >
          <Button danger disabled={!confirmed}>
            清空本次看板记录
          </Button>
        </Popconfirm>
      </section>
    </div>
  );
}
