import { type ReactNode, type ButtonHTMLAttributes, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-wm">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "quiet" | "danger";
};

export function Button({ variant = "ghost", className = "", ...props }: BtnProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed";
  const styles = {
    primary: "bg-gilt text-ink hover:bg-[#d4b170]",
    ghost: "border border-line text-paper hover:border-gilt/60 hover:bg-raised",
    quiet: "text-mist hover:text-paper",
    danger: "text-[#c98b8b] hover:text-[#e0a0a0]",
  }[variant];
  return <button className={`${base} ${styles} ${className}`} {...props} />;
}

export function Card({
  children,
  className = "",
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-line bg-surface ${
        onClick ? "cursor-pointer transition-colors hover:border-gilt/50 hover:bg-raised" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-mute">{children}</div>
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      className={`text-mute transition-transform duration-200 ${open ? "rotate-180" : ""}`}
    >
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Collapsible({
  title,
  meta,
  children,
  defaultOpen = false,
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-line bg-surface">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <span className="flex items-center gap-3">
          <Eyebrow>{title}</Eyebrow>
          {meta != null && <span className="text-xs text-mute">{meta}</span>}
        </span>
        <Chevron open={open} />
      </button>
      {open && <div className="border-t border-line-soft px-5 py-4">{children}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-mist">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-gilt" />
      {label}
    </div>
  );
}

export function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-line bg-surface p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

export function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-mist">{label}</span>
      <input
        className="w-full rounded-lg border border-line bg-ink px-3.5 py-2.5 text-sm text-paper placeholder:text-mute focus:border-gilt focus:outline-none"
        {...props}
      />
    </label>
  );
}

export function TextArea({
  label,
  ...props
}: { label?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block">
      {label && <span className="mb-1.5 block text-xs font-medium text-mist">{label}</span>}
      <textarea
        className="w-full resize-y rounded-lg border border-line bg-ink px-3.5 py-3 text-sm leading-relaxed text-paper placeholder:text-mute focus:border-gilt focus:outline-none"
        {...props}
      />
    </label>
  );
}
