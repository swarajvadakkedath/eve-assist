import type { ExecutionSession } from "../execution/session/types";

export type InspectorTab =
  | "summary" | "timeline" | "logs" | "tools" | "files"
  | "permissions" | "performance" | "metadata" | "raw";

export const INSPECTOR_TABS: { id: InspectorTab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "timeline", label: "Timeline" },
  { id: "logs", label: "Logs" },
  { id: "tools", label: "Tools" },
  { id: "files", label: "Files" },
  { id: "permissions", label: "Permissions" },
  { id: "performance", label: "Performance" },
  { id: "metadata", label: "Metadata" },
  { id: "raw", label: "Raw Event" },
];

export interface InspectorProps {
  session: ExecutionSession;
  onClose: () => void;
}
