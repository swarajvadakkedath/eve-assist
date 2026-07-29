import type { ComponentType } from "react";

export interface WorkspaceDefinition {
  id: string;
  label: string;
  icon?: string;
  component: ComponentType<any>;
}

export interface WorkspaceRegistryProps {
  workspaces: WorkspaceDefinition[];
  activeId: string;
  fallback?: ComponentType<{ workspaceId: string }>;
}

function DefaultFallback({ workspaceId }: { workspaceId: string }) {
  return (
    <div className="pr-workspace-empty">
      Unknown workspace: {workspaceId}
    </div>
  );
}

function WorkspaceRegistry({
  workspaces,
  activeId,
  fallback: Fallback = DefaultFallback,
}: WorkspaceRegistryProps) {
  const workspace = workspaces.find((w) => w.id === activeId);

  if (!workspace) {
    return <Fallback workspaceId={activeId} />;
  }

  const Component = workspace.component;
  return <Component />;
}

export default WorkspaceRegistry;
