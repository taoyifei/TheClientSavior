export type CustomerProfile = {
  monthly_fee: number;
  customer_type: string;
  tenure_years: number;
  has_broadband: boolean;
  wants_device: boolean;
  family_mobile_count: number;
  wants_port_out: boolean;
};

export type Policy = {
  id: string;
  title: string;
  category: string;
  price: string;
  target: string;
  keywords: string[];
  benefits: string[];
  conditions: string[];
  risk_notes: string[];
  script_hint: string;
};

export type DemoCase = {
  name: string;
  phone?: string;
  complaint: string;
  profile: CustomerProfile;
};

export type Customer = {
  phone_masked: string;
  customer_name?: string;
  source?: "static_customer" | "dashboard_history" | string;
  monthly_fee: number;
  customer_type: string;
  tenure_years: number;
  has_broadband: boolean;
  wants_device: boolean;
  family_mobile_count: number;
  wants_port_out: boolean;
  plan_name?: string;
  plan_data_gb?: number | null;
  last_month_usage_gb?: number | null;
  overage_fee?: number | null;
  recent_complaint_count?: number;
  recommended_hint?: string;
  last_complaint_summary?: string;
  last_risk_level?: string;
  last_top_business?: string;
  last_status?: string;
};

export type CustomerLookupResponse = {
  found: boolean;
  customer: Customer | null;
  message: string;
  source: "static_customer" | "dashboard_history" | "none" | string;
};

export type CustomerAnalysis = {
  complaint_type?: string;
  emotion?: string;
  risk_level?: string;
  key_needs?: string[];
  summary?: string;
};

export type RecommendedPolicy = {
  policy_id?: string;
  title?: string;
  category?: string;
  price?: string;
  rank?: number;
  local_score?: number;
  local_reasons?: string[];
  reason?: string;
  talking_point?: string;
  benefits?: string[];
  conditions?: string[];
  risk_notes?: string[];
  policy?: Partial<Policy>;
};

export type RetentionScript = {
  opening?: string;
  solution?: string;
  risk_disclosure?: string;
  next_step?: string;
};

export type TopBusiness = {
  title: string;
  category: string;
  price: string;
  reason: string;
  talking_point: string;
  benefits?: string[];
  risk_notes?: string[];
};

export type OverageStatus = {
  status: string;
  label: string;
  reason: string;
  usage_text: string;
  fee_text: string;
};

export type DecisionSummary = {
  overage: OverageStatus;
  top_business: TopBusiness;
  risk_level: string;
  complaint_type: string;
  emotion: string;
  follow_priority: string;
  customer_value: string;
  customer_tags: string[];
};

export type AgentResult = {
  customer_analysis: CustomerAnalysis;
  recommended_policies: RecommendedPolicy[];
  retention_script: RetentionScript;
  internal_notes: string[];
  mode: "llm" | "fallback" | string;
  model: string;
  elapsed_seconds: number;
  cached: boolean;
  llm_error?: string | null;
  phone_masked?: string;
  decision_summary?: DecisionSummary;
};

export type GeneratePayload = {
  phone: string;
  complaint: string;
  profile: CustomerProfile;
  use_llm: boolean;
};

export type AppConfig = {
  llm_configured: boolean;
  model: string;
  timeout: number;
  base_url: string;
};

export type DashboardMetrics = {
  total_cases: number;
  high_risk_cases: number;
  high_risk_percent: number;
  priority_wait_count: number;
  llm_success_count: number;
  fallback_count: number;
  average_elapsed: number;
};

export type DashboardRecord = {
  sequence: number;
  generated_at: string;
  phone_masked: string;
  complaint_type: string;
  risk_level: string;
  follow_priority: string;
  overage_label: string;
  top_business: string;
  emotion: string;
  customer_value: string;
  customer_tags: string;
  monthly_fee: number;
  customer_type: string;
  wants_port_out: string;
  status: string;
  mode: string;
  elapsed_seconds: number;
  complaint_summary: string;
};

export type DashboardResponse = {
  metrics: DashboardMetrics;
  risk_queue: DashboardRecord[];
  complaint_type_counter: Record<string, number>;
  policy_counter: Record<string, number>;
};
