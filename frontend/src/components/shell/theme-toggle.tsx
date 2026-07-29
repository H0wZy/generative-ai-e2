"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

type Theme = "light" | "dark";

// O tema já foi aplicado pelo script inline do <head> antes da pintura. Aqui
// só lemos o que está no <html> e alternamos — nada de provider nem contexto.
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    setTheme((document.documentElement.dataset.theme as Theme) ?? "dark");
  }, []);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Modo privativo sem localStorage: o tema vale para esta sessão.
    }
    setTheme(next);
  }

  return (
    <Button
      variant="ghost"
      onClick={toggle}
      aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}
      // suppressHydrationWarning: no servidor não há tema conhecido.
      suppressHydrationWarning
    >
      {theme === "dark" ? "Claro" : "Escuro"}
    </Button>
  );
}
