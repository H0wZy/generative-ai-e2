import { redirect } from "next/navigation";

// Rota antiga do quadro Kanban, mantida só para links já em circulação
// (specs/009 — consolidada em /agile/quadro). Redirect de servidor: não
// deixa a rota antiga no histórico (mesmo padrão de app/assistant/page.tsx).
export default async function KanbanRedirectPage() {
  redirect("/agile/quadro?escopo=board");
}
