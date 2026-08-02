// Textarea nativo, sem primitivo do Base UI por trás — mesmo caso de
// `ui/table.tsx`: elemento HTML sem estado de interação que justifique um
// wrapper headless. Namespace `v0/` pelo mesmo motivo do Button ao lado:
// tokens próprios da tela do Assistente.
import { cn } from "@/lib/utils";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "v0-scrollbar-slim min-h-[40px] w-full resize-none bg-transparent text-[15px] leading-relaxed text-v0-foreground outline-none placeholder:text-transparent",
        className,
      )}
      {...props}
    />
  );
}

export { Textarea };
