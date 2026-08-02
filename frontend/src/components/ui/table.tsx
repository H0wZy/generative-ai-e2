import { cn } from "@/lib/utils";

/** Rola dentro do próprio contêiner a partir de 360 px (FR-009). */
function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div data-slot="table-container" className="overflow-x-auto">
      <table
        data-slot="table"
        className={cn("w-full min-w-[40rem] border-collapse text-sm", className)}
        {...props}
      />
    </div>
  );
}

// Estilo do cabeçalho (maiúsculas, cor apagada) mora aqui via seletor de
// filho — `TableRow` fica neutro, reaproveitável em corpo e cabeçalho, como
// no shadcn original.
function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:text-xs [&_tr]:uppercase [&_tr]:tracking-wide [&_tr]:text-muted-foreground", className)}
      {...props}
    />
  );
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={className} {...props} />;
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn("border-b border-divider text-left last:border-0", className)}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th data-slot="table-head" className={cn("px-3 py-2 font-medium", className)} {...props} />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td data-slot="table-cell" className={cn("px-3 py-2 align-middle", className)} {...props} />
  );
}

export { Table, TableHeader, TableBody, TableRow, TableHead, TableCell };
