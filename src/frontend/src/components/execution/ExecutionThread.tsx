import type { ExecutionNode as NodeData } from "./types";
import ExecutionNode from "./ExecutionNode";

export interface ExecutionThreadProps {
  nodes: NodeData[];
}

function ExecutionThread({ nodes }: ExecutionThreadProps) {
  if (nodes.length === 0) return null;

  return (
    <div className="pr-exec-thread" role="list" aria-label="Execution steps">
      {nodes.map((node, i) => (
        <ExecutionNode key={node.id} node={node} isLast={i === nodes.length - 1} />
      ))}
    </div>
  );
}

export default ExecutionThread;
