import axios from "axios";
import type {
  AppConfig,
  CustomerLookupResponse,
  DashboardResponse,
  DemoCase,
  GeneratePayload,
  AgentResult,
  Policy
} from "./types";

const defaultBaseUrl = `${window.location.protocol}//${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultBaseUrl,
  timeout: 10000
});

export async function getConfig(): Promise<AppConfig> {
  const response = await api.get<AppConfig>("/api/config");
  return response.data;
}

export async function testLLM(): Promise<Record<string, unknown>> {
  const response = await api.post<Record<string, unknown>>("/api/llm/test");
  return response.data;
}

export async function getPolicies(): Promise<Policy[]> {
  const response = await api.get<Policy[]>("/api/policies");
  return response.data;
}

export async function getDemoCases(): Promise<DemoCase[]> {
  const response = await api.get<DemoCase[]>("/api/demo-cases");
  return response.data;
}

export async function lookupCustomer(
  phone: string
): Promise<CustomerLookupResponse> {
  const response = await api.get<CustomerLookupResponse>("/api/customers/lookup", {
    params: { phone }
  });
  return response.data;
}

export async function generatePlan(payload: GeneratePayload): Promise<AgentResult> {
  const response = await api.post<AgentResult>("/api/generate", payload, {
    timeout: 20000
  });
  return response.data;
}

export async function getDashboard(): Promise<DashboardResponse> {
  const response = await api.get<DashboardResponse>("/api/dashboard");
  return response.data;
}

export async function resetDashboard(): Promise<{ ok: boolean }> {
  const response = await api.post<{ ok: boolean }>("/api/dashboard/reset");
  return response.data;
}

export function exportDashboardCsvUrl(): string {
  return `${api.defaults.baseURL}/api/dashboard/export`;
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail || error.response?.data?.message;
    if (detail) return String(detail);
    if (error.code === "ECONNABORTED") {
      return "请求超时，请检查模型接口或后端服务。";
    }
    if (error.message === "Network Error") {
      return "无法连接后端，请确认 FastAPI 已启动，且 CORS/局域网地址配置正确。";
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "未知错误";
}
