import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Card no formato shadcn (slots + subcomponentes), mas mantendo o atalho
 * `title`/`action` que as 17 chamadas do projeto já usam — trocar todas por
 * `CardHeader`/`CardTitle` seria churn sem ganho visual nenhum. Quem precisar
 * de cabeçalho mais rico compõe com os subcomponentes abaixo.
 *
 * A elevação vem de `shadow-sm` (anel + sombra, ver `globals.css`), não de
 * `border`: é o que mantém a hairline discreta em vez de uma borda clara.
 */
function Card({
  title,
  action,
  children,
  className,
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section data-slot="card" className={cn("rounded-lg bg-card p-4 shadow-sm", className)}>
      {(title || action) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {action}
        </CardHeader>
      )}
      {children}
    </section>
  );
}

function CardHeader({ className, ...props }: React.ComponentProps<"header">) {
  return (
    <header
      data-slot="card-header"
      className={cn("mb-3 flex items-center justify-between gap-3", className)}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }: React.ComponentProps<"h2">) {
  return (
    <h2
      data-slot="card-title"
      className={cn("text-sm font-medium text-card-foreground", className)}
      {...props}
    />
  );
}

function CardDescription({ className, ...props }: React.ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("", className)} {...props} />;
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("mt-3 flex items-center gap-2", className)}
      {...props}
    />
  );
}

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
