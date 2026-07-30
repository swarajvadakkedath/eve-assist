export interface Model {
  id: string;
  displayName: string;
  provider: string;
  contextLength: number;
  maxOutput: number;
  supportsStreaming: boolean;
  supportsVision: boolean;
  supportsImageGeneration: boolean;
  supportsAudio: boolean;
  supportsReasoning: boolean;
  supportsFunctionCalling: boolean;
  supportsEmbeddings: boolean;
  supportsThinking: boolean;
  supportsJSON: boolean;
  enabled: boolean;
  isFree: boolean;
  recommended: boolean;
  deprecated: boolean;
  speed: number;
  quality: number;
  costPer1kInput: number;
  costPer1kOutput: number;
}

export interface ProviderInfo {
  id: string;
  type: string;
  name: string;
  endpoint_url?: string;
  organization?: string;
  temperature?: number;
  max_tokens?: number;
  streaming_enabled?: boolean;
  is_default?: boolean;
  has_api_key?: boolean;
  status: string;
  latency_ms?: number | null;
  last_checked?: string | null;
  models: Model[];
  created_at?: string;
  updated_at?: string;
}

export interface RoutingEntry {
  id: string;
  label: string;
  description?: string;
  provider_id: string | null;
  model_id: string | null;
}

export interface ProviderType {
  id: string;
  name: string;
  needs_endpoint: boolean;
  default_endpoint: string;
  has_models_endpoint: boolean;
}

export const ROUTING_CATEGORIES: RoutingEntry[] = [
  { id: "general_chat", label: "General Chat", description: "Everyday conversations and Q&A", provider_id: null, model_id: null },
  { id: "coding", label: "Coding", description: "Code generation, debugging, reviews", provider_id: null, model_id: null },
  { id: "vision", label: "Vision", description: "Image analysis and understanding", provider_id: null, model_id: null },
  { id: "reasoning", label: "Reasoning", description: "Complex reasoning and problem-solving", provider_id: null, model_id: null },
  { id: "fallback", label: "Fallback", description: "Used when primary provider fails", provider_id: null, model_id: null },
];

export interface ModelFilters {
  free: boolean;
  vision: boolean;
  reasoning: boolean;
  streaming: boolean;
  functionCalling: boolean;
  largeContext: boolean;
  fast: boolean;
  highQuality: boolean;
}

export type RoutingPolicy = "auto" | "strict" | "allow_fallback";

export type CommercialPolicy = "free_only" | "no_direct_paid" | "allow_paid";

export const ROUTING_POLICY_OPTIONS: { value: RoutingPolicy; label: string; description: string }[] = [
  { value: "auto", label: "Auto", description: "Eve may choose another eligible route when needed." },
  { value: "strict", label: "Strict", description: "Use exactly this provider/account and model." },
  { value: "allow_fallback", label: "Allow Fallback", description: "Prefer this selection but permit fallback when unavailable." },
];

export const COMMERCIAL_POLICY_OPTIONS: { value: CommercialPolicy; label: string; description: string }[] = [
  { value: "free_only", label: "Free Only", description: "Use routes explicitly classified FREE or LOCAL." },
  { value: "no_direct_paid", label: "No Direct Paid", description: "Allow FREE, FREE_TIER, CREDIT_BASED, and LOCAL routes. Reject PAID." },
  { value: "allow_paid", label: "Allow Paid", description: "Paid routes may be used when necessary. This can incur provider charges." },
];

export const FALLBACK_REASON_LABELS: Record<string, string> = {
  none: "",
  same_model_alternate_instance: "Alternate account",
  same_provider_alternate_model: "Alternate model",
  free_alternate_provider: "Free provider fallback",
  free_tier_alternate_provider: "Free-tier fallback",
  credit_alternate_provider: "Included-credit fallback",
  local_alternate: "Local fallback",
  paid_alternate: "Paid fallback",
};

export const COMMERCIAL_STATUS_LABELS: Record<string, string> = {
  FREE: "Free",
  FREE_TIER: "Free Tier",
  CREDIT_BASED: "Included Credits",
  LOCAL: "Local",
  PAID: "Paid",
  UNKNOWN: "",
};
