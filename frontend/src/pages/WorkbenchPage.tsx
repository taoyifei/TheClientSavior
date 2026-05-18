import { Button, message, Spin } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import { useState } from "react";
import { generatePlan, getErrorMessage, lookupCustomer, testLLM } from "../api/client";
import type {
  AgentResult,
  Customer,
  CustomerProfile,
  DemoCase
} from "../api/types";
import ComplaintIntakePanel from "../components/ComplaintIntakePanel";
import CustomerSnapshot from "../components/CustomerSnapshot";
import DecisionSummary from "../components/DecisionSummary";
import DemoCaseBar from "../components/DemoCaseBar";
import EmptyState from "../components/EmptyState";
import InternalNotes from "../components/InternalNotes";
import NumberLookupBar from "../components/NumberLookupBar";
import PolicyRecommendationGrid from "../components/PolicyRecommendationGrid";
import ScriptTimeline from "../components/ScriptTimeline";
import TopBusinessCard from "../components/TopBusinessCard";

type WorkbenchPageProps = {
  demoCases: DemoCase[];
  onDashboardChanged: () => Promise<void>;
};

const DEFAULT_PROFILE: CustomerProfile = {
  monthly_fee: 129,
  customer_type: "存量",
  tenure_years: 3,
  has_broadband: false,
  wants_device: false,
  family_mobile_count: 1,
  wants_port_out: false
};

function normalizePhone(value: string) {
  return value.replace(/\s+/g, "").replace(/-/g, "").trim();
}

function isStrictPhone(value: string) {
  return /^\d{11}$/.test(normalizePhone(value));
}

function profileFromCustomer(customer: Customer): CustomerProfile {
  return {
    monthly_fee: Number(customer.monthly_fee || 0),
    customer_type: customer.customer_type || "存量",
    tenure_years: Number(customer.tenure_years || 0),
    has_broadband: Boolean(customer.has_broadband),
    wants_device: Boolean(customer.wants_device),
    family_mobile_count: Number(customer.family_mobile_count || 0),
    wants_port_out: Boolean(customer.wants_port_out)
  };
}

function buildMarkdown(result: AgentResult, phoneMasked: string) {
  const summary = result.decision_summary;
  const lines = [
    "# 客户挽留方案",
    "",
    "## 客户决策摘要",
    `- 手机号：${phoneMasked || "未填写"}`,
    `- 是否超套：${summary?.overage.label || "待分析"}`,
    `- 推荐业务：${summary?.top_business.title || "待生成"}`,
    `- 风险等级：${summary?.risk_level || result.customer_analysis.risk_level || ""}`,
    `- 投诉类型：${summary?.complaint_type || result.customer_analysis.complaint_type || ""}`,
    `- 跟进优先级：${summary?.follow_priority || "待定"}`,
    "",
    "## 推荐政策 Top 3",
    ...result.recommended_policies.slice(0, 3).map((policy, index) => {
      return `${index + 1}. ${policy.title || policy.policy_id}：${policy.reason || ""}`;
    }),
    "",
    "## 四段式话术",
    `- 安抚开场：${result.retention_script.opening || ""}`,
    `- 方案介绍：${result.retention_script.solution || ""}`,
    `- 风险说明：${result.retention_script.risk_disclosure || ""}`,
    `- 下一步引导：${result.retention_script.next_step || ""}`,
    "",
    "## 内部提醒",
    ...result.internal_notes.map((note) => `- ${note}`)
  ];
  return lines.join("\n");
}

function downloadMarkdown(result: AgentResult, phoneMasked: string) {
  const markdown = buildMarkdown(result, phoneMasked);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "client_savior_plan.md";
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function WorkbenchPage({
  demoCases,
  onDashboardChanged
}: WorkbenchPageProps) {
  const [phone, setPhone] = useState("");
  const [lookupStatus, setLookupStatus] = useState("");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [complaint, setComplaint] = useState("");
  const [profile, setProfile] = useState<CustomerProfile>(DEFAULT_PROFILE);
  const [useLlm, setUseLlm] = useState(true);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const doLookup = async (targetPhone = phone) => {
    const normalizedPhone = normalizePhone(targetPhone);
    if (normalizedPhone && !isStrictPhone(normalizedPhone)) {
      message.warning("手机号格式不正确，请输入 11 位手机号；也可以留空继续演示。");
      return undefined;
    }
    if (!normalizedPhone) {
      setLookupStatus("未填写手机号，可继续手动补充画像。");
      setCustomer(null);
      return undefined;
    }
    setPhone(normalizedPhone);
    setLookupLoading(true);
    try {
      const response = await lookupCustomer(normalizedPhone);
      setLookupStatus(response.message);
      if (response.found && response.customer) {
        setCustomer(response.customer);
        setProfile(profileFromCustomer(response.customer));
        if (response.source === "dashboard_history") {
          setLookupStatus("命中本次风险看板处理记录，已回填客户画像。");
          message.success("已从本次看板记录回填客户画像");
        } else if (response.source === "static_customer") {
          setLookupStatus("命中本地演示客户画像。");
          message.success("命中本地演示客户画像");
        }
      } else {
        setCustomer(null);
      }
      return response;
    } finally {
      setLookupLoading(false);
    }
  };

  const applyDemoCase = async (demoCase: DemoCase) => {
    const demoPhone = normalizePhone(demoCase.phone || "");
    setPhone(demoPhone);
    setComplaint(demoCase.complaint);
    setProfile(demoCase.profile || DEFAULT_PROFILE);
    setResult(null);
    if (demoPhone) {
      const response = await doLookup(demoPhone);
      if (!response?.found) setProfile(demoCase.profile || DEFAULT_PROFILE);
    }
  };

  const clearAll = () => {
    setPhone("");
    setLookupStatus("");
    setCustomer(null);
    setComplaint("");
    setProfile(DEFAULT_PROFILE);
    setResult(null);
  };

  const handleGenerate = async () => {
    const normalizedPhone = normalizePhone(phone);
    if (normalizedPhone && !isStrictPhone(normalizedPhone)) {
      message.warning("手机号格式不正确，请输入 11 位手机号；也可以留空继续演示。");
      return;
    }
    if (!complaint.trim()) {
      message.warning("请先录入客户投诉内容。");
      return;
    }
    setGenerating(true);
    try {
      const response = await generatePlan({
        phone: normalizedPhone,
        complaint,
        profile,
        use_llm: useLlm
      });
      setPhone(normalizedPhone);
      setResult(response);
      await onDashboardChanged();
      message.success(
        response.mode === "llm" ? "云端模型已生成方案" : "已切换本地模板兜底"
      );
    } catch (error) {
      message.error(getErrorMessage(error));
    } finally {
      setGenerating(false);
    }
  };

  const handleTestLLM = async () => {
    try {
      const response = await testLLM();
      if (response.ok) {
        message.success(`LLM 连通正常，耗时 ${response.elapsed_seconds} 秒`);
      } else {
        message.error(`失败原因：${response.error}`);
      }
    } catch (error) {
      message.error(getErrorMessage(error));
    }
  };

  return (
    <div className="workbench-page">
      <NumberLookupBar
        phone={phone}
        lookupStatus={lookupStatus}
        loading={lookupLoading}
        onPhoneChange={setPhone}
        onLookup={() => doLookup()}
        onClear={clearAll}
        onTestLLM={handleTestLLM}
      />
      <DemoCaseBar demoCases={demoCases} onSelect={applyDemoCase} />
      <CustomerSnapshot customer={customer} />
      <DecisionSummary result={result} customer={customer} complaint={complaint} />
      <div className="workspace-grid">
        <ComplaintIntakePanel
          complaint={complaint}
          profile={profile}
          useLlm={useLlm}
          loading={generating}
          onComplaintChange={setComplaint}
          onProfileChange={setProfile}
          onUseLlmChange={setUseLlm}
          onGenerate={handleGenerate}
          onClear={clearAll}
        />
        <section className="recommendation-workspace">
          {generating && (
            <div className="loading-panel">
              <Spin />
              <div>
                <strong>云端模型分析中</strong>
                <p>政策召回 → 客户画像分析 → 生成首推业务 → 输出四段式话术</p>
              </div>
            </div>
          )}
          {!result && !generating && (
            <EmptyState
              title="等待生成客户挽留方案"
              body="号码查询 → 客户画像 → 模型分析 → 推荐政策与四段式话术。"
            />
          )}
          {result && (
            <>
              <div className="result-status-strip">
                <span>{result.mode === "llm" ? "云端模型生成" : "本地模板兜底"}</span>
                <span>模型：{result.model}</span>
                <span>耗时：{result.elapsed_seconds.toFixed(2)} 秒</span>
                <span>{result.cached ? "命中缓存" : "实时生成"}</span>
              </div>
              {result.llm_error && <div className="warning-strip">{result.llm_error}</div>}
              <TopBusinessCard result={result} />
              <PolicyRecommendationGrid policies={result.recommended_policies} />
              <ScriptTimeline script={result.retention_script} />
              <InternalNotes notes={result.internal_notes} />
              <Button
                icon={<DownloadOutlined />}
                onClick={() =>
                  downloadMarkdown(
                    result,
                    result.phone_masked || customer?.phone_masked || "未填写"
                  )
                }
              >
                下载 Markdown
              </Button>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
