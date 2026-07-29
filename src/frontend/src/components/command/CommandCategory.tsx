import type { CommandCategoryProps } from "./types";

function CommandCategory({ label, count }: CommandCategoryProps) {
  return (
    <div className="pr-cmd-category" role="presentation">
      <span className="pr-cmd-category-label">{label}</span>
      {count !== undefined && (
        <span className="pr-cmd-category-count" aria-label={`${count} items`}>{count}</span>
      )}
    </div>
  );
}

export default CommandCategory;
