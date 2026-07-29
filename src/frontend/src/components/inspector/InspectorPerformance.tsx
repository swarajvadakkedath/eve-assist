import type { ExecutionSession } from "../execution/session/types";

export interface InspectorPerformanceProps {
  session: ExecutionSession;
}

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function InspectorPerformance({ session }: InspectorPerformanceProps) {
  const totalDuration = session.durationMs || 0;
  const stepDurations = session.steps
    .map(s => ({ label: s.label, duration: s.durationMs || 0 }))
    .sort((a, b) => b.duration - a.duration);
  const longestStep = stepDurations[0];
  const totalStepTime = stepDurations.reduce((sum, s) => sum + s.duration, 0);

  const maxDuration = Math.max(totalDuration, totalStepTime, longestStep?.duration || 0);

  function barWidth(value: number): string {
    if (maxDuration === 0) return "0%";
    return `${(value / maxDuration) * 100}%`;
  }

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Performance">
      <h3 className="pr-inspector-section-title">Performance Breakdown</h3>

      <div className="pr-inspector-perf-bar">
        <span className="pr-inspector-perf-label">Total Duration</span>
        <div className="pr-inspector-perf-track">
          <div className="pr-inspector-perf-fill pr-inspector-perf-total" style={{ width: barWidth(totalDuration) }} />
        </div>
        <span className="pr-inspector-perf-value">{formatDuration(totalDuration)}</span>
      </div>

      <div className="pr-inspector-perf-bar">
        <span className="pr-inspector-perf-label">Steps Total</span>
        <div className="pr-inspector-perf-track">
          <div className="pr-inspector-perf-fill pr-inspector-perf-steps" style={{ width: barWidth(totalStepTime) }} />
        </div>
        <span className="pr-inspector-perf-value">{formatDuration(totalStepTime)}</span>
      </div>

      {longestStep && (
        <div className="pr-inspector-perf-bar">
          <span className="pr-inspector-perf-label">Longest Step</span>
          <div className="pr-inspector-perf-track">
            <div className="pr-inspector-perf-fill pr-inspector-perf-longest" style={{ width: barWidth(longestStep.duration) }} />
          </div>
          <span className="pr-inspector-perf-value">{longestStep.label} ({formatDuration(longestStep.duration)})</span>
        </div>
      )}

      <div className="pr-inspector-perf-table">
        <h4 className="pr-inspector-perf-table-title">Step Timing</h4>
        {session.steps.map(step => (
          <div key={step.id} className="pr-inspector-perf-row">
            <span className="pr-inspector-perf-row-label">{step.label}</span>
            <div className="pr-inspector-perf-track-sm">
              <div
                className="pr-inspector-perf-fill pr-inspector-perf-step-fill"
                style={{ width: barWidth(step.durationMs || 0) }}
              />
            </div>
            <span className="pr-inspector-perf-row-value">{formatDuration(step.durationMs)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default InspectorPerformance;
