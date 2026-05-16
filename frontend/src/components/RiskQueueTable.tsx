import { useState } from "react";
import { Button, Input, Select, Space, Table } from "antd";
import type { ColumnsType } from "antd/es/table";
import { exportDashboardCsvUrl } from "../api/client";
import type { DashboardRecord } from "../api/types";

type RiskQueueTableProps = {
  rows: DashboardRecord[];
};

const ALL = "全部";

const COLUMNS: ColumnsType<DashboardRecord> = [
  { title: "序号", dataIndex: "sequence", width: 90 },
  { title: "生成时间", dataIndex: "generated_at", width: 110 },
  { title: "手机号", dataIndex: "phone_masked", width: 130 },
  { title: "风险等级", dataIndex: "risk_level", width: 110 },
  { title: "跟进优先级", dataIndex: "follow_priority", width: 120 },
  { title: "是否超耗", dataIndex: "overage_label", width: 120 },
  { title: "推荐业务", dataIndex: "top_business", width: 220 },
  { title: "投诉类型", dataIndex: "complaint_type", width: 140 },
  { title: "客户情绪", dataIndex: "emotion", width: 120 },
  { title: "客户价值", dataIndex: "customer_value", width: 120 },
  { title: "客户标签", dataIndex: "customer_tags", width: 180 },
  { title: "当前月租", dataIndex: "monthly_fee", width: 110 },
  { title: "客户类型", dataIndex: "customer_type", width: 120 },
  { title: "明确携转", dataIndex: "wants_port_out", width: 110 },
  { title: "处理状态", dataIndex: "status", width: 130 },
  { title: "模式", dataIndex: "mode", width: 140 },
  { title: "耗时", dataIndex: "elapsed_seconds", width: 100 },
  { title: "投诉摘要", dataIndex: "complaint_summary", width: 280 }
];

export default function RiskQueueTable({ rows }: RiskQueueTableProps) {
  const [risk, setRisk] = useState(ALL);
  const [type, setType] = useState(ALL);
  const [status, setStatus] = useState(ALL);
  const [phone, setPhone] = useState("");
  const complaintTypes = Array.from(
    new Set(rows.map((row) => row.complaint_type).filter(Boolean))
  );
  const statuses = Array.from(new Set(rows.map((row) => row.status).filter(Boolean)));
  const filtered = rows.filter((row) => {
    return (
      (risk === ALL || row.risk_level === risk) &&
      (type === ALL || row.complaint_type === type) &&
      (status === ALL || row.status === status) &&
      (!phone || row.phone_masked.includes(phone))
    );
  });

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3>客户风险队列</h3>
          <p>默认按风险排序，高风险和待优先跟进客户靠前。</p>
        </div>
        <Button href={exportDashboardCsvUrl()} target="_blank">
          导出 CSV
        </Button>
      </div>
      <Space wrap className="filter-row">
        <Select
          value={risk}
          options={[ALL, "高", "中", "低"].map((value) => ({
            label: `风险：${value}`,
            value
          }))}
          onChange={setRisk}
        />
        <Select
          value={type}
          options={[ALL, ...complaintTypes].map((value) => ({
            label: `投诉：${value}`,
            value
          }))}
          onChange={setType}
        />
        <Select
          value={status}
          options={[ALL, ...statuses].map((value) => ({
            label: `状态：${value}`,
            value
          }))}
          onChange={setStatus}
        />
        <Input
          placeholder="搜索手机号后四位"
          value={phone}
          onChange={(event) => setPhone(event.target.value)}
          allowClear
        />
      </Space>
      <Table
        rowKey={(row) => String(row.sequence)}
        columns={COLUMNS}
        dataSource={filtered}
        pagination={{ pageSize: 8 }}
        scroll={{ x: 1800 }}
      />
    </section>
  );
}
