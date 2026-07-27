"""
Chunking de arquivos Markdown por heading.

Estratégia:
  - Cada heading (# ## ### ...) inicia um novo chunk.
  - O conteúdo é acumulado até o próximo heading do mesmo nível ou superior.
  - heading_path registra a hierarquia completa (ex: "Decisões > RAG > Modelo").
  - start_line / end_line são 1-indexados para rastreabilidade.
  - token_count é uma estimativa por whitespace split (suficiente para MVP).

Limites de tamanho configuráveis via parâmetros — sem valores hard-coded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class Chunk:
    """Representa um trecho de texto com metadados de proveniência."""

    content: str
    heading_path: str   # ex: "Decisões > Banco de Dados"
    start_line: int     # 1-indexado
    end_line: int       # 1-indexado, inclusivo
    token_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.token_count = len(self.content.split())

    def is_empty(self) -> bool:
        return not self.content.strip()


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


def _heading_level(line: str) -> tuple[int, str] | None:
    """Retorna (nível, texto) se a linha for um heading, senão None."""
    m = _HEADING_RE.match(line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return None


def chunk_markdown(
    text: str,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
    min_tokens: int = 1,
) -> list[Chunk]:
    """
    Divide o texto Markdown em chunks por heading com sobreposição opcional.

    Args:
        text: Conteúdo completo do arquivo Markdown.
        max_tokens: Tamanho máximo de cada chunk em tokens (whitespace split).
        overlap_tokens: Tokens do final do chunk anterior incluídos no início do próximo.
        min_tokens: Chunks menores que este valor são descartados.

    Returns:
        Lista de Chunk, na ordem de aparição no documento.
    """
    lines = text.splitlines()
    chunks: list[Chunk] = []

    # Pilha da hierarquia de headings: [(nível, texto), ...]
    heading_stack: list[tuple[int, str]] = []

    # Acumulador do chunk atual
    current_lines: list[str] = []
    current_start: int = 1

    def flush(end_line: int) -> None:
        """Finaliza o chunk acumulado e adiciona à lista."""
        if not current_lines:
            return
        content = "\n".join(current_lines).strip()
        path = " > ".join(h for _, h in heading_stack) if heading_stack else ""
        chunk = Chunk(
            content=content,
            heading_path=path,
            start_line=current_start,
            end_line=end_line,
        )
        if not chunk.is_empty() and chunk.token_count >= min_tokens:
            chunks.append(chunk)

    for lineno, line in enumerate(lines, start=1):
        parsed = _heading_level(line)

        if parsed is not None:
            level, title = parsed

            # Fecha o chunk anterior antes de abrir novo
            flush(end_line=lineno - 1)

            # Atualiza a pilha de headings
            # Remove headings do mesmo nível ou mais profundos
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))

            # Inicia novo chunk incluindo o heading
            current_lines = [line]
            current_start = lineno
        else:
            current_lines.append(line)

    # Último chunk
    flush(end_line=len(lines))

    # Divide chunks que excedem max_tokens (fallback por tamanho)
    result: list[Chunk] = []
    for chunk in chunks:
        if chunk.token_count <= max_tokens:
            result.append(chunk)
        else:
            result.extend(
                _split_oversized(chunk, max_tokens=max_tokens, overlap=overlap_tokens)
            )

    return result


def _split_oversized(
    chunk: Chunk,
    max_tokens: int,
    overlap: int,
) -> list[Chunk]:
    """
    Divide um chunk que excede max_tokens em sub-chunks com sobreposição.
    Preserva heading_path e distribui start/end_line proporcionalmente.
    """
    words = chunk.content.split()
    total_lines = chunk.end_line - chunk.start_line + 1
    sub_chunks: list[Chunk] = []

    step = max(1, max_tokens - overlap)
    pos = 0
    sub_idx = 0

    while pos < len(words):
        window = words[pos : pos + max_tokens]
        content = " ".join(window)

        # Estimativa de linhas proporcional
        proportion = pos / len(words)
        end_proportion = (pos + len(window)) / len(words)
        est_start = chunk.start_line + int(proportion * total_lines)
        est_end = chunk.start_line + int(end_proportion * total_lines)

        sub_chunks.append(
            Chunk(
                content=content,
                heading_path=chunk.heading_path,
                start_line=est_start,
                end_line=min(est_end, chunk.end_line),
            )
        )
        pos += step
        sub_idx += 1

    return sub_chunks


def iter_markdown_files(
    root: str,
    allowed_prefixes: list[str] | None = None,
) -> Generator[str, None, None]:
    """
    Itera recursivamente sobre arquivos .md abaixo de root.

    Args:
        root: Diretório raiz da busca.
        allowed_prefixes: Se fornecido, apenas arquivos cujo caminho começa
                          com um dos prefixos são retornados (allowlist de paths).

    Yields:
        Caminhos absolutos de arquivos .md encontrados. Symlinks que apontam
        para fora de `root` são rejeitados (não seguem para fora da allowlist).
    """
    from pathlib import Path

    root_path = Path(root).resolve()
    for candidate in sorted(root_path.rglob("*.md")):
        md_file = candidate.resolve()  # resolve symlinks para o alvo real
        try:
            md_file.relative_to(root_path)
        except ValueError:
            continue  # symlink escapou de root — rejeita
        path_str = str(md_file)
        if allowed_prefixes:
            if not any(path_str.startswith(p) for p in allowed_prefixes):
                continue
        yield path_str
