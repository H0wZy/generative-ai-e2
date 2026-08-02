"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type TicketPriority = "low" | "medium" | "high" | "urgent";

export interface TicketFormValues {
  subject: string;
  description: string;
  priority: TicketPriority;
  category: string;
}

const PRIORITY_OPTIONS: [TicketPriority, string][] = [
  ["low", "Baixa"],
  ["medium", "Média"],
  ["high", "Alta"],
  ["urgent", "Urgente"],
];

const FIELD =
  "min-h-9 rounded-md border border-divider bg-surface px-2 text-sm text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

// Reusado para criar (FR-049) e editar (FR-052) — o formulário em si não sabe
// qual das duas ações o `onSubmit` do chamador executa.
export function TicketForm({
  initialValues,
  onSubmit,
  submitLabel,
  disabled = false,
}: {
  initialValues?: Partial<TicketFormValues>;
  onSubmit: (values: TicketFormValues) => void | Promise<void>;
  submitLabel: string;
  disabled?: boolean;
}) {
  const [subject, setSubject] = useState(initialValues?.subject ?? "");
  const [description, setDescription] = useState(initialValues?.description ?? "");
  const [priority, setPriority] = useState<TicketPriority>(initialValues?.priority ?? "medium");
  const [category, setCategory] = useState(initialValues?.category ?? "");

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit({ subject, description, priority, category });
      }}
      className="flex flex-col gap-3"
    >
      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">Assunto</span>
        <input
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          required
          maxLength={255}
          className={FIELD}
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">Descrição</span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={4}
          maxLength={20_000}
          className={`${FIELD} min-h-24 resize-y py-2`}
        />
      </label>

      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Prioridade</span>
          <Select
            value={priority}
            onValueChange={(value) => setPriority(value as TicketPriority)}
            items={PRIORITY_OPTIONS.map(([value, label]) => ({ value, label }))}
          >
            <SelectTrigger className={`${FIELD} min-w-40 gap-2`} aria-label="Prioridade">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITY_OPTIONS.map(([value, label]) => (
                <SelectItem key={value} value={value} className="text-sm">
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs text-muted-foreground">Categoria</span>
          <input
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            maxLength={80}
            className={FIELD}
          />
        </label>
      </div>

      <Button type="submit" variant="default" disabled={disabled} className="self-start">
        {submitLabel}
      </Button>
    </form>
  );
}
