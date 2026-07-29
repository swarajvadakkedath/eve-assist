import { useCallback } from "react";
import type { CommandInputProps } from "./types";

function CommandInput({ value, onChange, onKeyDown, placeholder, inputRef }: CommandInputProps) {
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value),
    [onChange]
  );

  return (
    <div className="pr-cmd-input-wrapper">
      <span className="pr-cmd-input-icon" aria-hidden="true">{'\u2318'}</span>
      <input
        ref={inputRef}
        className="pr-cmd-input"
        type="text"
        value={value}
        onChange={handleChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder || "Type a command or search..."}
        aria-label="Command search"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        autoFocus
      />
      {value && (
        <button
          className="pr-cmd-input-clear"
          onClick={() => onChange("")}
          aria-label="Clear search"
          title="Clear"
        >
          {'\u2715'}
        </button>
      )}
    </div>
  );
}

export default CommandInput;
