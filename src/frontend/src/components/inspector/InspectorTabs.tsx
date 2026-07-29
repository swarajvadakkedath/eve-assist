import type { InspectorTab } from "./types";
import { INSPECTOR_TABS } from "./types";

export interface InspectorTabsProps {
  active: InspectorTab;
  onChange: (tab: InspectorTab) => void;
}

function InspectorTabs({ active, onChange }: InspectorTabsProps) {
  return (
    <div className="pr-inspector-tabs" role="tablist" aria-label="Execution inspector tabs">
      {INSPECTOR_TABS.map(tab => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          className={`pr-inspector-tab ${active === tab.id ? "pr-inspector-tab-active" : ""}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export default InspectorTabs;
