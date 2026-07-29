import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center gap-3 px-4 py-16 text-center">
      <p className="text-sm font-medium text-text">Página não encontrada</p>
      <p className="text-xs text-muted">
        O endereço acessado não existe nesta plataforma.
      </p>
      <Link
        href="/"
        className="text-sm text-link underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
      >
        Voltar para a Home
      </Link>
    </div>
  );
}
