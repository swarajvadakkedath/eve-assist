export interface AioProvider {
  id: string;
  type: string;
  name: string;
  endpoint_url?: string;
  organization?: string;
  streaming_enabled: boolean;
  is_default: boolean;
  has_api_key: boolean;
  status: string;
  latency_ms?: number | null;
  last_checked?: string | null;
  models: AioModel[];
  created_at?: string;
  updated_at?: string;
}

export interface AioModel {
  id: string;
  displayName?: string;
  providerId?: string;
  providerName?: string;
  providerType?: string;
  providerInstanceId?: string;
  contextWindow?: number;
  contextLength?: number;
  maxOutputTokens?: number;
  maxOutput?: number;
  supportsStreaming?: boolean;
  supportsVision?: boolean;
  supportsReasoning?: boolean;
  supportsThinking?: boolean;
  supportsTools?: boolean;
  supportsFunctionCalling?: boolean;
  supportsJSON?: boolean;
  supportsEmbeddings?: boolean;
  supportsAudio?: boolean;
  supportsImageGeneration?: boolean;
  speed?: number;
  quality?: number;
  latency?: number;
  isFree?: boolean;
  commercialStatus?: string;
  availability?: string;
  recommended?: boolean;
  deprecated?: boolean;
  experimental?: boolean;
  enabled?: boolean;
  pricing?: { input: number; output: number };
  costPer1kInput?: number;
  costPer1kOutput?: number;
  provider?: string;
  provider_instance_id?: string;
  provider_type?: string;
}

export interface AioHealthEntry {
  provider_id: string;
  state: string;
  status: string;
  last_check: number;
  last_success: number;
  last_failure: number;
  consecutive_failures: number;
  latency_ms: number;
  error_message: string;
  rate_limit: {
    state: string;
    cooldown_remaining: number;
    retry_after_seconds: number;
    consecutive_429s: number;
    daily_quota_exhausted: boolean;
  };
  total_checks: number;
  successful_checks: number;
  success_rate: number;
  health_score: number;
}

export interface AioHealthSnapshot {
  type: string;
  timestamp: number;
  latency_ms: number;
  health_score?: number;
  success_rate?: number;
  status?: string;
  state?: string;
}

export interface AioRoutingEntry {
  id: string;
  label: string;
  description?: string;
  provider_id: string | null;
  model_id: string | null;
}

export interface AioRoutingCategory {
  id: string;
  label: string;
  capabilities: string[];
}

export interface AioDiagnostics {
  commercial_policy: string;
  routing_config: AioRoutingEntry[];
  health: Record<string, AioHealthEntry>;
  rate_limits: Record<string, {
    state: string;
    cooldown_remaining: number;
    retry_after_seconds: number;
    consecutive_429s: number;
    daily_quota_exhausted: boolean;
  }>;
  capabilities: Record<string, {
    models: AioModel[];
    capabilities: string[];
  }>;
}

export interface AioActivityEvent {
  id: string;
  timestamp: number;
  type: "health_check" | "model_refresh" | "routing_decision" | "provider_recovery" | "error" | "warning" | "rate_limit" | "background_task";
  provider_id?: string;
  message: string;
  details?: Record<string, unknown>;
  severity: "info" | "warning" | "error" | "success";
}

export interface AioErrorEvent {
  error_id: string;
  timestamp: string;
  category: string;
  severity: string;
  module: string;
  message: string;
  root_cause: string;
  likely_cause: string;
  recovery_suggestions: string[];
  auto_recovery_attempted: boolean;
  recovery_result: string | null;
  conversation_id: string | null;
  request_id: string | null;
  provider: string | null;
  model: string | null;
  tool: string | null;
  http_status: number | null;
  exception_type: string | null;
  stack_trace: string | null;
  duration: number | null;
  recoverable: boolean;
  retryable: boolean;
  resolved: boolean;
}

export interface AioErrorStats {
  total: number;
  resolved: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  top_failing_providers: Record<string, number>;
  most_common_errors: Record<string, number>;
  auto_recoveries: { attempted: number; recovered: number };
  recovery_success_rate: number;
}

export interface AioTimelineEvent {
  timestamp: string;
  type: string;
  message: string;
  error_id: string;
  category: string;
  severity: string;
  provider: string | null;
  model: string | null;
  resolved: boolean;
}

export interface AioMetrics {
  totalRequests: number;
  avgLatencyMs: number;
  avgTokens: number;
  fallbackCount: number;
  failureCount: number;
  providerDistribution: Record<string, number>;
  modelDistribution: Record<string, number>;
  estimatedMoneySaved: number;
}

export type AioTabId = "dashboard" | "providers" | "models" | "smartrouter" | "health" | "activity" | "settings" | "recovery";

export interface AioTab {
  id: AioTabId;
  label: string;
  icon: string;
}

export const AIO_TABS: AioTab[] = [
  { id: "dashboard", label: "Dashboard", icon: "📊" },
  { id: "providers", label: "Providers", icon: "🔗" },
  { id: "models", label: "Models", icon: "🤖" },
  { id: "smartrouter", label: "SmartRouter", icon: "🧭" },
  { id: "health", label: "Health", icon: "💚" },
  { id: "recovery", label: "Recovery", icon: "🔧" },
  { id: "activity", label: "Activity", icon: "📋" },
  { id: "settings", label: "Settings", icon: "⚙" },
];

export const PROVIDER_ICONS: Record<string, string> = {
  openai: "🟢", google: "🔵", groq: "🟣", openrouter: "🟠",
  ollama: "🦙", deepinfra: "🌊", cloudflare: "☁️",
  huggingface: "🤗", nvidia: "💚",
};

export const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
  openai: "OpenAI Platform", google: "Google AI Studio", groq: "GroqCloud",
  openrouter: "OpenRouter", ollama: "Ollama", deepinfra: "DeepInfra",
  cloudflare: "Cloudflare Workers AI", huggingface: "Hugging Face Inference",
  nvidia: "NVIDIA Build (NIM)",
};

export const STATE_COLORS: Record<string, string> = {
  healthy: "#22c55e",
  degraded: "#f59e0b",
  unreachable: "#ef4444",
  invalid_key: "#ef4444",
  rate_limited: "#f97316",
  quota_exceeded: "#ef4444",
  unknown: "#6b7280",
  connected: "#22c55e",
  offline: "#ef4444",
  not_configured: "#6b7280",
};
