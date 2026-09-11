import { forwardRef, useId, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";

export function PageHeader({ eyebrow, title, children, action }: {
  eyebrow?: string; title: string; children?: ReactNode; action?: ReactNode;
}) {
  return <header className="cf-page-header">
    <div className="min-w-0">
      {eyebrow && <p className="cf-eyebrow">{eyebrow}</p>}
      <h1>{title}</h1>
      {children && <p className="cf-page-description">{children}</p>}
    </div>
    {action && <div className="cf-header-actions">{action}</div>}
  </header>;
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; };
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field({ label, error, className = "", id, ...props }, ref) {
  const uid = useId();
  const inputId = id ?? uid;
  return <label className="cf-field" htmlFor={inputId}>
    <span>{label}{props.required && <span aria-hidden="true" className="text-slate-400"> *</span>}</span>
    <input {...props} ref={ref} id={inputId} aria-invalid={error ? true : undefined}
      aria-describedby={error ? `${inputId}-error` : props["aria-describedby"]} className={`cf-input ${className}`} />
    {error && <span id={`${inputId}-error`} className="cf-field-error">{error}</span>}
  </label>;
});

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; };
export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(function TextArea({ label, className = "", id, ...props }, ref) {
  const uid = useId();
  return <label className="cf-field" htmlFor={id ?? uid}><span>{label}</span>
    <textarea {...props} id={id ?? uid} ref={ref} className={`cf-input cf-textarea ${className}`} />
  </label>;
});

export function Button({ children, secondary = false, danger = false, className = "", type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { secondary?: boolean; danger?: boolean; }) {
  return <button {...props} type={type} className={`cf-button ${danger ? "cf-button-danger" : secondary ? "cf-button-secondary" : "cf-button-primary"} ${className}`}>{children}</button>;
}
