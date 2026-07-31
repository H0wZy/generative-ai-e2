// Button no estilo shadcn/base-nova, só para a tela /assistant — namespace
// `v0/` deliberado: existe já um Button (frontend/src/components/ui/button.tsx)
// no tema ink/brass usado pelo resto do app, este não o substitui (escopo:
// spec 003, "só o Assistente por agora").
import { Button as ButtonPrimitive } from "@base-ui/react/button";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-v0-ring focus-visible:ring-3 focus-visible:ring-v0-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-v0-primary text-v0-primary-foreground hover:opacity-90",
        outline:
          "border-v0-border bg-v0-background hover:bg-v0-muted hover:text-v0-foreground",
        secondary: "bg-v0-secondary text-v0-secondary-foreground hover:bg-v0-secondary/80",
        ghost: "hover:bg-v0-accent hover:text-v0-accent-foreground",
        destructive:
          "bg-v0-destructive/10 text-v0-destructive hover:bg-v0-destructive/20",
      },
      size: {
        default: "h-9 gap-1.5 px-3",
        sm: "h-7 gap-1 rounded-[min(var(--radius-v0-md),12px)] px-2.5 text-[0.8rem]",
        icon: "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
