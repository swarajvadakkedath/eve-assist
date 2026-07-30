import { useState, useCallback } from "react";
import { fetchApi } from "../../services/api";

interface ConnectionTesterProps {
  providerId: string;
  disabled?: boolean;
}

interface TestResult {
  success: boolean;
  status?: string;
  latency_ms?: number;
  error?: string;
}

const STATUS_LABELS: Record<string, string> = {
  connected: "Connected",
  invalid_key: "Invalid API key",
  rate_limited: "Rate limited",
  offline: "Offline",
  error: "Provider error",
};

const STATUS_ICONS: Record<string, string> = {
  connected: "\u2713",
  invalid_key: "\u26A0",
  rate_limited: "\u23F3",
  offline: "\u2717",
  error: "\u2717",
};

export default function ConnectionTester({ providerId, disabled }: ConnectionTesterProps) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);

  const runTest = useCallback(async () => {
    setTesting(true);
    setResult(null);
    try {
      const res = await fetchApi(`/providers/${providerId}/test`, { method: "POST" });
      const data: TestResult = await res.json();
      setResult(data);
    } catch {
      setResult({ success: false, status: "error", error: "Request failed" });
    } finally {
      setTesting(false);
    }
  }, [providerId]);

  const statusClass = result?.success
    ? "pr-test-success"
    : result?.status === "invalid_key"
    ? "pr-test-warn"
    : "pr-test-fail";

  const statusLabel = result?.success
    ? "Connected"
    : STATUS_LABELS[result?.status || ""] || result?.error || "Connection failed";

  const statusIcon = result?.success
    ? "\u2713"
    : STATUS_ICONS[result?.status || ""] || "\u2717";

  return (
    <div className="pr-connection-tester">
      <button
        className="btn btn-primary"
        onClick={runTest}
        disabled={testing || disabled}
        style={{ minWidth: 140 }}
      >
        {testing ? "Testing..." : "Test Connection"}
      </button>

      {result && (
        <div className={`pr-test-result ${statusClass}`}>
          <span className="pr-test-icon">{statusIcon}</span>
          <span className="pr-test-text">
            {statusLabel}
            {result.latency_ms != null && ` \u00B7 ${result.latency_ms}ms`}
          </span>
        </div>
      )}
    </div>
  );
}
