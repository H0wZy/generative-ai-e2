import type { ReactNode } from "react";

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`bg-surface rounded-lg shadow-sm p-4 ${className}`}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 mb-3">
          {title && <h2 className="text-sm font-medium text-text">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
