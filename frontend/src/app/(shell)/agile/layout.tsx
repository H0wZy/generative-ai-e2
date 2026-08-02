import { AgileTabs } from "@/components/agile/agile-tabs";

// `<main>` do shell (shell-chrome.tsx) já rola sozinho — este layout só
// empilha as abas acima do conteúdo de cada página, sem criar mais um
// contêiner de scroll aninhado.
export default function AgileLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <AgileTabs />
      {children}
    </div>
  );
}
