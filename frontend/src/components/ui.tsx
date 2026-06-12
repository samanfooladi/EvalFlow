/** Small custom design system — no UI framework, Tailwind only. */
import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

const btnVariants = {
  primary:
    "bg-accent-600 hover:bg-accent-500 text-white shadow-sm disabled:bg-surface-600",
  ghost:
    "bg-transparent hover:bg-surface-700 text-ink-300 border border-surface-600 hover:border-surface-500",
  danger: "bg-finding-500/90 hover:bg-finding-500 text-white",
} as const;

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof btnVariants;
}) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/70 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 disabled:active:translate-y-0 ${btnVariants[variant]} ${className}`}
      {...props}
    />
  );
}

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string }
>(function Input({ label, error, className = "", ...props }, ref) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-ink-300">
          {label}
        </span>
      )}
      <input
        ref={ref}
        className={`w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-2 text-sm text-ink-100 placeholder:text-ink-600 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500 ${error ? "border-finding-500" : ""} ${className}`}
        {...props}
      />
      {error && <span className="mt-1 block text-xs text-finding-400">{error}</span>}
    </label>
  );
});

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }
>(function Textarea({ label, className = "", ...props }, ref) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-ink-300">
          {label}
        </span>
      )}
      <textarea
        ref={ref}
        className={`w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-2 text-sm leading-7 text-ink-100 placeholder:text-ink-600 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500 ${className}`}
        {...props}
      />
    </label>
  );
});

export function Select({
  label,
  children,
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label?: string }) {
  return (
    <label className="block">
      {label && (
        <span className="mb-1.5 block text-sm font-medium text-ink-300">
          {label}
        </span>
      )}
      <select
        className={`w-full rounded-lg border border-surface-600 bg-surface-800 px-3 py-2 text-sm text-ink-100 focus:border-accent-500 focus:outline-none ${className}`}
        {...props}
      >
        {children}
      </select>
    </label>
  );
}

const badgeTones = {
  neutral: "bg-surface-700 text-ink-300",
  accent: "bg-accent-600/15 text-accent-400 ring-1 ring-accent-600/30",
  finding: "bg-finding-500/15 text-finding-400 ring-1 ring-finding-500/30",
  compliant: "bg-compliant-500/15 text-compliant-400 ring-1 ring-compliant-500/30",
  warn: "bg-warn-400/15 text-warn-400 ring-1 ring-warn-400/30",
} as const;

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: keyof typeof badgeTones;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeTones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-surface-700 bg-surface-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-ink-100">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-ink-500 hover:bg-surface-700 hover:text-ink-100"
            aria-label="بستن"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-surface-600 p-10 text-center text-sm text-ink-500">
      {children}
    </div>
  );
}

export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p className="rounded-lg bg-finding-500/10 px-3 py-2 text-sm text-finding-400">
      {children}
    </p>
  );
}
