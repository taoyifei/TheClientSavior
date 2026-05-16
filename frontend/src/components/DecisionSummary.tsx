import type { AgentResult, Customer, DecisionSummary as Summary } from "../api/types";

type DecisionSummaryProps = {
  result: AgentResult | null;
  customer: Customer | null;
  complaint: string;
};

function fallbackSummary(customer: Customer | null, complaint: string): Summary {
  const hasUsage =
    customer?.plan_data_gb !== undefined &&
    customer?.last_month_usage_gb !== undefined;
  const usageOver =
    hasUsage && Number(customer?.last_month_usage_gb) > Number(customer?.plan_data_gb);
  const suspiciousWords = ["超量", "超耗", "流量不够", "月底提醒", "扣费", "流量费"];
  const suspicious = suspiciousWords.some((word) => complaint.includes(word));
  const status = usageOver ? "是" : suspicious ? "疑似" : hasUsage ? "否" : "未知";
  const labelMap: Record<string, string> = {
    是: "已超耗",
    疑似: "疑似超耗",
    否: "未发现超耗",
    未知: "暂无数据"
  };
  return {
    overage: {
      status,
      label: labelMap[status],
      reason: usageOver
        ? "上月用量超过套餐流量"
        : suspicious
          ? "投诉内容出现超量或扣费表达"
          : "等待模型结合投诉进一步判断",
      usage_text: hasUsage
        ? `上月${customer?.last_month_usage_gb}G / 套餐${customer?.plan_data_gb}G`
        : "暂无用量",
      fee_text:
        customer?.overage_fee !== undefined ? `超耗费用${customer.overage_fee}元` : ""
    },
    top_business: {
      title: "待生成",
      category: "暂无",
      price: "",
      reason: "输入投诉后自动生成推荐业务。",
      talking_point: ""
    },
    risk_level: "待分析",
    complaint_type: "待分析",
    emotion: "待分析",
    follow_priority: "待定",
    customer_value: "待分析",
    customer_tags: []
  };
}

function toneByValue(value: string) {
  if (["高", "P1", "已超耗"].includes(value)) return "danger";
  if (["中", "P2", "疑似超耗"].includes(value)) return "warning";
  if (["低", "P3", "未发现超耗"].includes(value)) return "success";
  return "neutral";
}

export default function DecisionSummary({
  result,
  customer,
  complaint
}: DecisionSummaryProps) {
  const summary = result?.decision_summary || fallbackSummary(customer, complaint);
  const strongCards = [
    {
      label: "是否超耗",
      value: summary.overage.label,
      desc: summary.overage.usage_text || summary.overage.reason,
      tone: toneByValue(summary.overage.label)
    },
    {
      label: "风险等级",
      value: summary.risk_level,
      desc: summary.customer_value,
      tone: toneByValue(summary.risk_level)
    },
    {
      label: "跟进优先级",
      value: summary.follow_priority,
      desc: summary.customer_tags.join(" / ") || "待定",
      tone: toneByValue(summary.follow_priority)
    }
  ];
  const weakCards = [
    {
      label: "投诉类型",
      value: summary.complaint_type,
      desc: "用于匹配政策场景"
    },
    {
      label: "客户情绪",
      value: summary.emotion,
      desc: "影响安抚强度"
    }
  ];

  return (
    <section className="decision-center">
      <div className="section-heading compact">
        <div>
          <h2>AI 决策驾驶舱</h2>
          <p>先判断风险，再选择首推业务和话术执行路径。</p>
        </div>
      </div>
      <div className="decision-layout">
        <article className="decision-hero">
          <span className="decision-eyebrow">首推业务</span>
          <h3>{summary.top_business.title}</h3>
          <p>{summary.top_business.reason || "输入投诉后自动生成推荐业务。"}</p>
          <div className="decision-hero-meta">
            <span>{summary.top_business.category || "待生成"}</span>
            {summary.top_business.price && <strong>{summary.top_business.price}</strong>}
          </div>
        </article>
        <div className="decision-card-grid">
          {strongCards.map((card) => (
            <div key={card.label} className={`kpi-card primary ${card.tone}`}>
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <p>{card.desc}</p>
            </div>
          ))}
          {weakCards.map((card) => (
            <div key={card.label} className="kpi-card secondary neutral">
              <span>{card.label}</span>
              <strong>{card.value}</strong>
              <p>{card.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
