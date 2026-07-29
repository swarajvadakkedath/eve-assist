export interface ExecutionMetadataProps {
  items: { label: string; value: string }[];
}

function ExecutionMetadata({ items }: ExecutionMetadataProps) {
  if (items.length === 0) return null;
  return (
    <div className="pr-exec-metadata">
      {items.map((item, i) => (
        <span key={i} className="pr-exec-metadata-item">
          <span className="pr-exec-metadata-label">{item.label}</span>
          <span className="pr-exec-metadata-value">{item.value}</span>
        </span>
      ))}
    </div>
  );
}

export default ExecutionMetadata;
