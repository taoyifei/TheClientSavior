import type { Customer } from "../api/types";
import EmptyState from "./EmptyState";

type CustomerSnapshotProps = {
  customer: Customer | null;
};

function yesNo(value?: boolean) {
  return value ? "是" : "否";
}

export default function CustomerSnapshot({ customer }: CustomerSnapshotProps) {
  if (!customer) {
    return (
      <section className="customer-360 compact">
        <EmptyState
          title="未查询到客户画像"
          body="可继续手动录入投诉与画像，手机号不会进入模型输入。"
        />
      </section>
    );
  }

  const usage =
    customer.plan_data_gb !== undefined && customer.last_month_usage_gb !== undefined
      ? `${customer.last_month_usage_gb}G / ${customer.plan_data_gb}G`
      : "暂无";
  const overageTone = Number(customer.overage_fee || 0) > 0 ? "danger" : "";

  const items = [
    ["手机号", customer.phone_masked, ""],
    ["客户类型", customer.customer_type, ""],
    ["当前套餐", customer.plan_name || "未登记", ""],
    ["当前月租", `${customer.monthly_fee} 元`, ""],
    ["网龄", `${customer.tenure_years} 年`, ""],
    ["上月/套餐流量", usage, overageTone],
    ["超耗费用", `${customer.overage_fee || 0} 元`, overageTone],
    ["家庭号码", `${customer.family_mobile_count} 个`, ""],
    ["宽带状态", yesNo(customer.has_broadband), ""],
    ["携转风险", yesNo(customer.wants_port_out), customer.wants_port_out ? "danger" : ""]
  ];

  return (
    <section className="customer-360">
      <div className="section-heading">
        <div>
          <h2>客户 360</h2>
          <p>{customer.recommended_hint || "本地演示客户画像"}</p>
        </div>
      </div>
      <div className="snapshot-grid">
        {items.map(([label, value, tone]) => (
          <div key={label} className={`snapshot-card ${tone}`}>
            <span className="snapshot-label">{label}</span>
            <strong className="snapshot-value">{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
