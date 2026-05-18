import { Tag } from "antd";
import type { Policy } from "../api/types";

type PolicyCardProps = {
  policy: Policy;
};

export default function PolicyCard({ policy }: PolicyCardProps) {
  return (
    <article className="policy-card library-card">
      <div className="policy-card-head">
        <Tag color="blue">{policy.category}</Tag>
        <strong>{policy.price}</strong>
      </div>
      <h3>{policy.title}</h3>
      <p className="muted-text">{policy.target}</p>
      <div className="chip-row">
        {policy.benefits.slice(0, 4).map((benefit) => (
          <span className="chip green" key={benefit}>
            {benefit}
          </span>
        ))}
      </div>
      <p>
        <strong>办理条件：</strong>
        {policy.conditions.slice(0, 2).join("；")}
      </p>
      <p>
        <strong>风险提醒：</strong>
        {policy.risk_notes.slice(0, 2).join("；")}
      </p>
    </article>
  );
}
