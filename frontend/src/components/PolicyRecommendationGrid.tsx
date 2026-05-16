import type { RecommendedPolicy } from "../api/types";
import { getPolicyField } from "../utils/policy";

type PolicyRecommendationGridProps = {
  policies: RecommendedPolicy[];
};

export default function PolicyRecommendationGrid({
  policies
}: PolicyRecommendationGridProps) {
  if (!policies.length) return null;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3>推荐政策 Top 3</h3>
          <p>按客户诉求、画像和政策匹配度排序。</p>
        </div>
      </div>
      <div className="policy-grid">
        {policies.slice(0, 3).map((policy, index) => {
          const category = getPolicyField(policy, "category", "政策");
          const price = getPolicyField(policy, "price", "");
          const benefits = getPolicyField<string[]>(policy, "benefits", []);
          const conditions = getPolicyField<string[]>(policy, "conditions", []);
          const riskNotes = getPolicyField<string[]>(policy, "risk_notes", []);
          return (
            <article className="policy-card" key={`${policy.policy_id}-${index}`}>
              <div className="policy-rank">TOP {policy.rank || index + 1}</div>
              <h4>{policy.title || policy.policy?.title || policy.policy_id}</h4>
              <p className="muted-text">
                {category}
                {price ? ` · ${price}` : ""}
              </p>
              <p>
                <strong>推荐理由：</strong>
                {policy.reason}
              </p>
              {policy.talking_point && (
                <p>
                  <strong>客服卖点：</strong>
                  {policy.talking_point}
                </p>
              )}
              <div className="chip-row">
                {benefits.slice(0, 3).map((benefit) => (
                  <span className="chip blue" key={benefit}>
                    {benefit}
                  </span>
                ))}
              </div>
              <div className="chip-row">
                {conditions.slice(0, 2).map((condition) => (
                  <span className="chip green" key={condition}>
                    {condition}
                  </span>
                ))}
                {riskNotes.slice(0, 2).map((risk) => (
                  <span className="chip orange" key={risk}>
                    {risk}
                  </span>
                ))}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
