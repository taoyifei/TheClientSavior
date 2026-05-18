import type { Policy, RecommendedPolicy } from "../api/types";

export function getPolicyField<T>(
  item: RecommendedPolicy,
  key: keyof Policy,
  fallback: T
): T {
  const direct = item[key as keyof RecommendedPolicy];
  if (direct !== undefined && direct !== null && direct !== "") {
    return direct as T;
  }
  const nested = item.policy?.[key];
  if (nested !== undefined && nested !== null && nested !== "") {
    return nested as T;
  }
  return fallback;
}
