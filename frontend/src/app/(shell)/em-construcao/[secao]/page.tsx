import { notFound } from "next/navigation";

import { Card } from "@/components/ui/card";

// Uma rota dinâmica cobre as quatro seções não implementadas (FR-004).
// Quatro páginas idênticas seriam quatro arquivos para o mesmo conteúdo.
const SECOES: Record<string, { titulo: string; descricao: string }> = {
  assets: {
    titulo: "Assets",
    descricao:
      "Inventário de ativos vindo do Freshservice. A automação atual cobre tickets, não CMDB.",
  },
  "base-de-conhecimento": {
    titulo: "Base de Conhecimento",
    descricao:
      "Artigos do Freshservice. A busca semântica da documentação técnica já existe no Assistente de IA.",
  },
  automacoes: {
    titulo: "Automações",
    descricao:
      "Gestão das regras de roteamento pela tela. Hoje as regras vivem na configuração do backend.",
  },
  administracao: {
    titulo: "Administração",
    descricao:
      "Usuários, permissões e credenciais das integrações. Configuradas por variável de ambiente nesta fase.",
  },
};

export function generateStaticParams() {
  return Object.keys(SECOES).map((secao) => ({ secao }));
}

export default async function EmConstrucao({
  params,
}: {
  params: Promise<{ secao: string }>;
}) {
  const { secao } = await params;
  const info = SECOES[secao];
  if (!info) notFound();

  return (
    <div className="p-4 md:p-6">
      <Card title={info.titulo}>
        <div className="flex flex-col gap-2 py-6 text-center">
          <p className="text-sm font-medium text-text">Seção em construção</p>
          <p className="mx-auto max-w-prose text-xs text-muted-foreground">{info.descricao}</p>
        </div>
      </Card>
    </div>
  );
}
