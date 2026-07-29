import { forwardRef, useId, type InputHTMLAttributes } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, id: externalId, className = "", ...rest }, ref) => {
    const generatedId = useId();
    const inputId = externalId || generatedId;
    const errorId = error ? `${inputId}-error` : undefined;
    const hintId = hint && !error ? `${inputId}-hint` : undefined;

    const inputClasses = [
      "pr-input",
      error ? "pr-input-error" : "",
      className,
    ]
      .filter(Boolean)
      .join(" ");

    return (
      <div className="pr-input-wrapper">
        {label && (
          <label className="pr-input-label" htmlFor={inputId}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={inputClasses}
          aria-invalid={error ? true : undefined}
          aria-describedby={errorId || hintId}
          {...rest}
        />
        {error && (
          <span className="pr-input-error-text" id={errorId} role="alert">
            {error}
          </span>
        )}
        {hint && !error && (
          <span className="pr-input-hint" id={hintId}>
            {hint}
          </span>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";

export default Input;
