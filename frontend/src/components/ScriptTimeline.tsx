import type { RetentionScript } from "../api/types";

type ScriptTimelineProps = {
  script: RetentionScript;
};

export default function ScriptTimeline({ script }: ScriptTimelineProps) {
  const steps = [
    ["安抚开场", script.opening],
    ["方案介绍", script.solution],
    ["风险说明", script.risk_disclosure],
    ["下一步引导", script.next_step]
  ];

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <h3>四段式挽留话术</h3>
          <p>客服可直接照读，再根据系统办理结果调整。</p>
        </div>
      </div>
      <div className="script-timeline">
        {steps.map(([title, body], index) => (
          <div className="script-step" key={title}>
            <div className="step-index">{index + 1}</div>
            <div>
              <h4>{title}</h4>
              <p>{body || "待生成"}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
