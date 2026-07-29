import type { CommandShortcutProps } from "./types";

function CommandShortcut({ shortcut }: CommandShortcutProps) {
  const keys = shortcut.split("+");
  return (
    <span className="pr-cmd-shortcut" aria-hidden="true">
      {keys.map((key, i) => (
        <span key={i} className="pr-cmd-shortcut-key">
          {key === "Mod" ? "\u2318" : key === "Ctrl" ? "\u2303" : key === "Alt" ? "\u2325" : key === "Shift" ? "\u21E7" : key}
        </span>
      ))}
    </span>
  );
}

export default CommandShortcut;
