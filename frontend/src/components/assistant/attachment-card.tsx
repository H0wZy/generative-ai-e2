"use client";

import { useState } from "react";
import { FileText, X } from "lucide-react";

import { apiFetch } from "@/lib/api";
import type { AttachmentSummary } from "@/lib/types";
import {
  Attachment,
  AttachmentAction,
  AttachmentActions,
  AttachmentContent,
  AttachmentDescription,
  AttachmentMedia,
  AttachmentTitle,
  AttachmentTrigger,
} from "@/components/ui/attachment";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

// AttachmentSummary.status (backend) -> estado visual do componente shadcn.
function attachmentCardState(status: AttachmentSummary["status"]) {
  if (status === "ready") return "done" as const;
  if (status === "failed") return "error" as const;
  return "uploading" as const; // "received" | "processing"
}

interface AttachmentCardProps {
  attachment: AttachmentSummary;
  conversationId: string;
  sessionId: string;
  size?: "default" | "sm" | "xs";
  className?: string;
  /** Só no composer, antes do envio — mensagem já enviada não desanexa. */
  onRemove?: () => void;
}

/**
 * Card do documento anexado, clicável pra visualizar o conteúdo (specs/013
 * follow-up). Reaproveitado tanto no composer (com ação de remover) quanto
 * na mensagem enviada na transcrição (só leitura).
 */
export function AttachmentCard({
  attachment,
  conversationId,
  sessionId,
  size = "sm",
  className,
  onRemove,
}: AttachmentCardProps) {
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "error">("idle");
  const viewable = attachment.status === "ready";

  async function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next || content !== null || loadState === "loading") return;
    setLoadState("loading");
    const result = await apiFetch<{ file_name: string; content: string }>(
      `/api/v1/assistant/conversations/${conversationId}/attachment/content`,
      { headers: { "X-Session-Id": sessionId } },
    );
    if (result.ok) {
      setContent(result.data.content);
      setLoadState("idle");
    } else {
      setLoadState("error");
    }
  }

  const card = (
    <Attachment state={attachmentCardState(attachment.status)} size={size} className={className}>
      <AttachmentMedia>
        <FileText />
      </AttachmentMedia>
      <AttachmentContent>
        <AttachmentTitle>{attachment.file_name}</AttachmentTitle>
        <AttachmentDescription>
          {attachment.status === "failed"
            ? (attachment.error_reason ?? "Falha ao processar o documento.")
            : attachment.status === "ready"
              ? "Anexado"
              : "Processando…"}
        </AttachmentDescription>
      </AttachmentContent>
      {onRemove && (
        <AttachmentActions>
          <AttachmentAction aria-label={`Remover ${attachment.file_name}`} onClick={onRemove}>
            <X />
          </AttachmentAction>
        </AttachmentActions>
      )}
      {viewable && (
        <DialogTrigger render={<AttachmentTrigger aria-label={`Visualizar ${attachment.file_name}`} />} />
      )}
    </Attachment>
  );

  if (!viewable) return card;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {card}
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{attachment.file_name}</DialogTitle>
        </DialogHeader>
        <p className="text-xs text-muted-foreground">
          {(attachment.size_bytes / 1000).toFixed(1)} KB
          {content !== null ? ` · ${content.split("\n").length} linhas` : ""}
        </p>
        {loadState === "loading" && <p className="text-sm text-muted-foreground">Carregando…</p>}
        {loadState === "error" && (
          <p role="alert" className="text-sm text-destructive">
            Não foi possível carregar o conteúdo do documento.
          </p>
        )}
        {content !== null && (
          // Conteúdo do documento é não confiável: texto simples dentro de
          // <pre>, nunca HTML/Markdown (mesma regra de SourceAccordion).
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap break-words rounded-lg bg-elevated px-3.5 py-3 text-xs leading-relaxed text-muted-foreground">
            {content}
          </pre>
        )}
      </DialogContent>
    </Dialog>
  );
}
