import type { CommandPreviewProps } from "./types";

function CommandPreview({ data }: CommandPreviewProps) {
  if (!data) {
    return (
      <div className="pr-cmd-preview pr-cmd-preview-empty">
        <p className="pr-cmd-preview-empty-text">Select a command to preview</p>
      </div>
    );
  }

  const { item, description, category, shortcut, estimatedAction } = data;
  return (
    <div className="pr-cmd-preview">
      <h3 className="pr-cmd-preview-title">{item.name}</h3>
      <p className="pr-cmd-preview-desc">{description}</p>
      <dl className="pr-cmd-preview-details">
        <dt>Category</dt>
        <dd>{category}</dd>
        {shortcut && (
          <>
            <dt>Shortcut</dt>
            <dd><kbd className="pr-cmd-preview-kbd">{shortcut}</kbd></dd>
          </>
        )}
        <dt>Action</dt>
        <dd className="pr-cmd-preview-action">{estimatedAction}</dd>
      </dl>
    </div>
  );
}

export default CommandPreview;
