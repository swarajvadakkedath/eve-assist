import type { CommandItemRowProps } from "./types";
import CommandShortcut from "./CommandShortcut";

const CATEGORY_ICONS: Record<string, string> = {
  app: "[A]",
  workspace: "[W]",
  tool: "[T]",
  plugin: "[P]",
  conversation: "[C]",
  session: "[S]",
  memory: "[M]",
  browser: "[B]",
  voice: "[V]",
  vision: "[I]",
  developer: "[D]",
  file: "[F]",
  nlp: "[NL]",
  recent: "[R]",
};

function CommandItemRow({ item, selected, onSelect, onHover }: CommandItemRowProps) {
  return (
    <div
      className={`pr-cmd-item ${selected ? "pr-cmd-item-selected" : ""}`}
      role="option"
      aria-selected={selected}
      onClick={onSelect}
      onMouseEnter={onHover}
      data-command-id={item.id}
    >
      <span className="pr-cmd-item-icon" aria-hidden="true">
        {item.icon || CATEGORY_ICONS[item.category] || "[?]"}
      </span>
      <div className="pr-cmd-item-content">
        <span className="pr-cmd-item-name">{item.name}</span>
        <span className="pr-cmd-item-desc">{item.description}</span>
      </div>
      {item.shortcut && <CommandShortcut shortcut={item.shortcut} />}
    </div>
  );
}

export default CommandItemRow;
