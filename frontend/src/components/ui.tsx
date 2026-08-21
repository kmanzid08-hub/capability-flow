import {
    forwardRef,
    type ButtonHTMLAttributes,
    type InputHTMLAttributes,
    type ReactNode,
    type TextareaHTMLAttributes,
} from "react";

type PageHeaderProps = {
    eyebrow: string;
    title: string;
    children?: ReactNode;
    action?: ReactNode;
};

export function PageHeader({
    eyebrow,
    title,
    children,
    action,
}: PageHeaderProps) {
    return (
        <header className="mb-8 flex flex-col justify-between gap-5 border-b border-black/10 pb-7 sm:flex-row sm:items-end">
            <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-[.2em] text-evergreen">
                    {eyebrow}
                </p>

                <h1 className="font-serif text-4xl tracking-tight">{title}</h1>

                {children && (
                    <p className="mt-2 max-w-2xl text-sm text-slate-500">
                        {children}
                    </p>
                )}
            </div>

            {action}
        </header>
    );
}

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
    label: string;
    error?: string;
};

export const Field = forwardRef<HTMLInputElement, FieldProps>(
    function Field({ label, error, ...props }, ref) {
        return (
            <label className="block text-sm font-medium text-slate-700">
                {label}

                <input
                    ref={ref}
                    {...props}
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-evergreen focus:ring-2 focus:ring-evergreen/10"
                />

                {error && (
                    <span className="mt-1 block text-xs text-red-600">
                        {error}
                    </span>
                )}
            </label>
        );
    },
);

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
    label: string;
};

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
    function TextArea({ label, ...props }, ref) {
        return (
            <label className="block text-sm font-medium text-slate-700">
                {label}

                <textarea
                    ref={ref}
                    {...props}
                    className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 outline-none focus:border-evergreen focus:ring-2 focus:ring-evergreen/10"
                />
            </label>
        );
    },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    secondary?: boolean;
};

export function Button({
    children,
    secondary = false,
    ...props
}: ButtonProps) {
    return (
        <button
            {...props}
            className={`rounded-xl px-5 py-3 text-sm font-semibold transition disabled:opacity-50 ${secondary
                ? "border border-slate-200 bg-white hover:bg-slate-50"
                : "bg-evergreen text-white hover:bg-[#103d37]"
                }`}
        >
            {children}
        </button>
    );
}