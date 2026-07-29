// Cliente de API que nunca lança. Corpo de erro do backend nunca é exibido
// cru — `message` é sempre string escolhida por `kind`/`status` no frontend.
// Contrato: specs/002-unified-itsm-agile-ui/contracts/ui-routes.md

export type ApiErrorKind = "network" | "http" | "parse";

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: { kind: ApiErrorKind; status?: number; message: string } };

// `API_URL` é o nome já usado pelo compose para o servidor; o público existe
// para os componentes de cliente, que não enxergam a variável do servidor.
const API_BASE_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function messageFor(kind: ApiErrorKind, status?: number): string {
  if (kind === "network") return "Não foi possível conectar ao servidor.";
  if (kind === "parse") return "Resposta inesperada do servidor.";
  if (status === 404) return "Recurso não encontrado.";
  if (status === 401 || status === 403) return "Sem permissão para acessar este recurso.";
  if (status !== undefined && status >= 500) return "O servidor encontrou um erro.";
  return "Não foi possível completar a solicitação.";
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  let response: Response;
  try {
    // Painel operacional: número velho é pior que número lento.
    response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store", ...init });
  } catch {
    return { ok: false, error: { kind: "network", message: messageFor("network") } };
  }

  if (!response.ok) {
    return {
      ok: false,
      error: { kind: "http", status: response.status, message: messageFor("http", response.status) },
    };
  }

  try {
    const data = (await response.json()) as T;
    return { ok: true, data };
  } catch {
    return { ok: false, error: { kind: "parse", message: messageFor("parse") } };
  }
}
