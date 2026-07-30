"""
Inicialização do banco SQLite para o RAG local.

O banco persiste em rag/data/knowledge.db e é somente leitura para o MCP.
Não contém dados operacionais (PostgreSQL é o banco operacional).

Estratégia de vetores:
  - Tenta carregar sqlite-vec se disponível (enable_load_extension).
  - Caso contrário, usa fallback com tabela `embeddings_fallback` (BLOB)
    e busca cosine em Python puro — mesma interface pública.

O flag SQLITE_VEC_AVAILABLE indica qual modo está ativo.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Localização padrão do banco — pode ser sobrescrita em testes
DEFAULT_DB_PATH = Path(__file__).parent / "data" / "knowledge.db"

# Raiz do repositório (rag/ é filho direto dela) — usada para gravar
# file_path relativo em source_files, sem vazar o caminho absoluto/home
# do usuário nas respostas do MCP.
REPO_ROOT = Path(__file__).resolve().parent.parent


def to_repo_relative(path: str | Path) -> str:
    """
    Converte um caminho absoluto para relativo à raiz do repositório.
    Fora do repositório (ex.: diretórios temporários de teste), mantém
    o caminho original — não há home a vazar nesse caso.
    """
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)

# Versão do pipeline; incrementar ao alterar schema ou modelo
PIPELINE_VERSION = "1.0.0"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384
CHUNK_SIZE = 512   # tokens aproximados por chunk
CHUNK_OVERLAP = 64  # tokens de sobreposição entre chunks

# Detecta suporte a extensões SQLite no runtime atual
def _check_vec_support() -> bool:
    """Retorna True se sqlite-vec pode ser carregado neste Python."""
    conn = sqlite3.connect(":memory:")
    if not hasattr(conn, "enable_load_extension"):
        conn.close()
        return False
    try:
        import sqlite_vec  # noqa: F401
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


SQLITE_VEC_AVAILABLE: bool = _check_vec_support()

if SQLITE_VEC_AVAILABLE:
    logger.info("sqlite-vec disponível — usando busca vetorial nativa.")
else:
    logger.info("sqlite-vec indisponível — usando fallback cosine Python puro.")


def load_vec_extension(conn: sqlite3.Connection) -> None:
    """
    Carrega a extensão sqlite-vec na conexão fornecida.
    No-op se SQLITE_VEC_AVAILABLE é False.
    """
    if not SQLITE_VEC_AVAILABLE:
        return
    import sqlite_vec
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """
    Abre (ou cria) o banco SQLite, carregando sqlite-vec se disponível.

    Returns:
        Conexão com row_factory=sqlite3.Row para acesso por nome de coluna.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path = Path(db_path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    # DELETE, não WAL: o banco é servido depois via bind mount `:ro` (rag-search,
    # MCP) — WAL exige sidecar -wal/-shm gravável até para leitura, o que um
    # mount somente-leitura nunca permite.
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA foreign_keys=ON")
    load_vec_extension(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Cria as tabelas necessárias se ainda não existirem.
    Idempotente — seguro de chamar em banco já inicializado.
    """
    conn.executescript("""
        -- Configuração e reprodutibilidade do pipeline
        CREATE TABLE IF NOT EXISTS rag_settings (
            id               INTEGER PRIMARY KEY CHECK (id = 1),
            embedding_model  TEXT    NOT NULL,
            dimensions       INTEGER NOT NULL,
            chunk_size       INTEGER NOT NULL,
            overlap          INTEGER NOT NULL,
            pipeline_version TEXT    NOT NULL,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        -- Proveniência e controle de sincronização dos arquivos fonte
        CREATE TABLE IF NOT EXISTS source_files (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path    TEXT    NOT NULL UNIQUE,
            content_hash TEXT    NOT NULL,
            indexed_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            status       TEXT    NOT NULL DEFAULT 'active'
                             CHECK (status IN ('active', 'removed'))
        );

        -- Texto e posição de origem de cada chunk
        CREATE TABLE IF NOT EXISTS document_chunks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id      INTEGER NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
            content      TEXT    NOT NULL,
            heading_path TEXT    NOT NULL DEFAULT '',
            start_line   INTEGER NOT NULL DEFAULT 0,
            end_line     INTEGER NOT NULL DEFAULT 0,
            token_count  INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON document_chunks(file_id);

        -- Fallback: embeddings como BLOB quando sqlite-vec não está disponível
        CREATE TABLE IF NOT EXISTS embeddings_fallback (
            chunk_id  INTEGER PRIMARY KEY
                          REFERENCES document_chunks(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL
        );

        -- Metadados de embedding (modelo, versão)
        CREATE TABLE IF NOT EXISTS embedding_meta (
            chunk_id          INTEGER PRIMARY KEY
                                  REFERENCES document_chunks(id) ON DELETE CASCADE,
            embedding_model   TEXT NOT NULL,
            embedding_version TEXT NOT NULL,
            embedded_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)

    # Tabela virtual sqlite-vec — apenas se suportado
    if SQLITE_VEC_AVAILABLE:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "embeddings" not in tables:
            conn.execute(f"""
                CREATE VIRTUAL TABLE embeddings USING vec0(
                    chunk_id  INTEGER PRIMARY KEY,
                    embedding FLOAT[{EMBEDDING_DIMENSIONS}]
                )
            """)

    conn.commit()
    logger.debug("Schema inicializado.")


def upsert_settings(conn: sqlite3.Connection) -> None:
    """Insere ou atualiza a linha de configuração do pipeline."""
    conn.execute("""
        INSERT INTO rag_settings (id, embedding_model, dimensions, chunk_size, overlap, pipeline_version)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            embedding_model  = excluded.embedding_model,
            dimensions       = excluded.dimensions,
            chunk_size       = excluded.chunk_size,
            overlap          = excluded.overlap,
            pipeline_version = excluded.pipeline_version
    """, (EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, CHUNK_SIZE, CHUNK_OVERLAP, PIPELINE_VERSION))
    conn.commit()


def initialize_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """
    Abre o banco, inicializa o schema e registra as configurações.

    Use esta função como ponto de entrada principal.
    """
    conn = get_connection(db_path)
    init_schema(conn)
    upsert_settings(conn)
    logger.info("Banco RAG inicializado em %s", db_path or DEFAULT_DB_PATH)
    return conn
