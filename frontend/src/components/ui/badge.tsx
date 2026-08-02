import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * Badge no formato shadcn (cva + `data-slot`), com os tons que o produto já
 * usava no antigo `Tag`. Os pares fundo/texto são os mesmos de antes, sem um
 * único valor alterado: já foram verificados para 4.5:1 (FR-008) e as rampas
 * `neutral-*`/`accent-*` são a identidade brass do produto.
 */
const badgeVariants = cva(
  "inline-flex items-center rounded-sm px-2 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        neutral: "bg-neutral-800 text-neutral-200",
        accent: "bg-accent-800 text-accent-200",
        success: "bg-accent-2-800 text-accent-2-200",
        warning: "bg-neutral-700 text-neutral-100",
        danger: "bg-accent-900 text-accent-300",
      },
    },
    defaultVariants: {
      variant: "neutral",
    },
  },
);

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return (
    <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants, type BadgeVariant };
