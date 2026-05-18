import { Input, Select } from "antd";
import { useMemo, useState } from "react";
import type { Policy } from "../api/types";
import PolicyCard from "../components/PolicyCard";

type PolicyPageProps = {
  policies: Policy[];
};

export default function PolicyPage({ policies }: PolicyPageProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("全部");
  const categories = useMemo(
    () => ["全部", ...Array.from(new Set(policies.map((policy) => policy.category)))],
    [policies]
  );
  const filtered = policies.filter((policy) => {
    const text = [
      policy.title,
      policy.category,
      policy.price,
      policy.target,
      policy.benefits.join(" "),
      policy.keywords.join(" ")
    ].join(" ");
    return (
      (category === "全部" || policy.category === category) &&
      (!query || text.includes(query))
    );
  });

  return (
    <div className="policy-page">
      <section className="panel policy-toolbar">
        <div>
          <h2>政策货架</h2>
          <p>共 {policies.length} 张政策卡，供本地召回和模型生成引用。</p>
        </div>
        <Input.Search
          allowClear
          placeholder="搜索政策名称、权益或关键词"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <Select
          value={category}
          options={categories.map((value) => ({ label: value, value }))}
          onChange={setCategory}
        />
      </section>
      <div className="policy-grid library-grid">
        {filtered.map((policy) => (
          <PolicyCard key={policy.id} policy={policy} />
        ))}
      </div>
    </div>
  );
}
