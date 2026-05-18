import { Tag } from "antd";
import type { AgentResult } from "../api/types";
import { getPolicyField } from "../utils/policy";
import EmptyState from "./EmptyState";

type TopBusinessCardProps = {
  result: AgentResult | null;
};

export default function TopBusinessCard({ result }: TopBusinessCardProps) {
  const item = result?.recommended_policies?.[0];
  const top = result?.decision_summary?.top_business;
  if (!item && !top) {
    return (
      <EmptyState
        title="等待生成推荐业务"
        body="输入号码和投诉内容后，这里会直接展示首推业务、卖点和办理提醒。"
      />
    );
  }

  const title = top?.title || item?.title || item?.policy_id || "待生成";
  const category = top?.category || (item ? getPolicyField(item, "category", "推荐政策") : "推荐政策");
  const price = top?.price || (item ? getPolicyField(item, "price", "") : "");
  const benefits = top?.benefits || (item ? getPolicyField<string[]>(item, "benefits", []) : []);
  const riskNotes =
    top?.risk_notes || (item ? getPolicyField<string[]>(item, "risk_notes", []) : []);
  const reason = top?.reason || item?.reason || "";
  const talkingPoint = top?.talking_point || item?.talking_point || "";

  return (
    <section className="top-recommendation">
      <div className="top-badge">首推业务</div>
      <div className="top-rank">TOP 1</div>
      <h2>{title}</h2>
      <div className="top-meta">
        <Tag color="blue">{category}</Tag>
        {price && <Tag color="green">{price}</Tag>}
      </div>
      {reason && <p className="top-reason">{reason}</p>}
      {talkingPoint && <p className="top-talking">{talkingPoint}</p>}
      <div className="chip-row">
        {benefits.slice(0, 4).map((benefit) => (
          <span className="chip green" key={benefit}>
            {benefit}
          </span>
        ))}
      </div>
      <div className="chip-row">
        {riskNotes.slice(0, 3).map((risk) => (
          <span className="chip orange" key={risk}>
            {risk}
          </span>
        ))}
      </div>
    </section>
  );
}
