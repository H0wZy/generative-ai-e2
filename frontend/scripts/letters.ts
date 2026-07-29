#!/usr/bin/env node

/**
 * Banner CLI — Bootcamp GenAI E2
 * Estilo inspirado na referência: letras geométricas em blocos,
 * contorno/sombra deslocada e paleta coral/laranja.
 *
 * Roda automaticamente antes de `npm run dev` (script "predev"),
 * ou sozinho via `npm run banner`.
 *
 * Executado direto pelo Node (v22.18+), que remove os tipos em tempo de
 * carga — sem passo de build.
 */

import type { FontName } from "figlet";

type TextConfig = {
  value: string;
  colors: string[];
  row: number;
};

type Figlet = typeof import("figlet").default;
type Gradient = typeof import("gradient-string").default;

type RenderedText = {
  row: number;
  value: string;
  art: string;
  coloredArt: string;
  font: string;
};

const CONFIG: { fonts: FontName[]; texts: TextConfig[] } = {
  fonts: ["ANSI Shadow", "Doom", "Big"],

  texts: [
    {
      value: "TCS BOOTCAMP",
      colors: ["#f1eeec", "#c7c6c6"],
      row: 1,
    },
    {
      value: "GENERATIVE AI E2",
      colors: ["#ea5a12", "#e6a517"],
      row: 2,
    },
  ],
};

async function loadDependencies(): Promise<{
  figlet: Figlet;
  gradient: Gradient;
} | null> {
  try {
    const [figletModule, gradientModule] = await Promise.all([
      import("figlet"),
      import("gradient-string"),
    ]);

    return {
      figlet: figletModule.default ?? figletModule,
      gradient: gradientModule.default ?? gradientModule,
    };
  } catch (error) {
    console.error("\n\x1b[31m[Banner] Dependências não encontradas.\x1b[0m");
    console.error("Execute: npm install (figlet e gradient-string sao devDependencies)\n");
    console.error(`Detalhes: ${(error as Error).message}`);
    process.exitCode = 1;
    return null;
  }
}

function figletText(figlet: Figlet, text: string, font: FontName): Promise<string> {
  return new Promise((resolve, reject) => {
    figlet.text(
      text,
      {
        font,
        horizontalLayout: "default",
        verticalLayout: "default",
        width: Math.max(process.stdout.columns ?? 100, 80),
        whitespaceBreak: true,
      },
      (error, result) => {
        if (error) return reject(error);
        resolve(result ?? "");
      },
    );
  });
}

async function createBannerWithFallback(
  figlet: Figlet,
  text: string,
): Promise<{ art: string; font: string }> {
  let lastError: unknown;

  for (const font of CONFIG.fonts) {
    try {
      return {
        art: await figletText(figlet, text, font),
        font,
      };
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError ?? new Error(
    `Nenhuma fonte FIGlet pôde ser carregada para "${text}".`,
  );
}

function joinArtsHorizontally(arts: string[], spacing = 4): string {
  const separator = ' '.repeat(spacing);

  const splitArts = arts.map((art) => art.split('\n'));

  const maximumHeight = Math.max(
    ...splitArts.map((lines) => lines.length),
  );

  return Array.from({ length: maximumHeight }, (_, lineIndex) => {
    return splitArts
      .map((lines) => lines[lineIndex] ?? '')
      .join(separator);
  }).join('\n');
}

async function renderBanner(): Promise<void> {
  const dependencies = await loadDependencies();

  if (!dependencies) {
    return;
  }

  const { figlet, gradient } = dependencies;

  try {
    const renderedTexts: RenderedText[] = [];

    for (const textConfig of CONFIG.texts) {
      const { art, font } = await createBannerWithFallback(
        figlet,
        textConfig.value,
      );

      const textGradient = gradient(textConfig.colors);
      const coloredArt = textGradient.multiline(art);

      renderedTexts.push({
        row: textConfig.row,
        value: textConfig.value,
        art,
        coloredArt,
        font,
      });
    }

    // Agrupa os textos conforme a propriedade "row".
    const groupedRows = new Map<number, RenderedText[]>();

    for (const renderedText of renderedTexts) {
      const row = groupedRows.get(renderedText.row) ?? [];
      row.push(renderedText);
      groupedRows.set(renderedText.row, row);
    }

    // Ordena as linhas: row 1, row 2, row 3...
    const orderedRows = [...groupedRows.entries()].sort(
      ([rowA], [rowB]) => rowA - rowB,
    );

    const finalRows = orderedRows.map(([, texts]) => {
      return joinArtsHorizontally(
        texts.map((text) => text.coloredArt),
        4,
      );
    });

    process.stdout.write('\n');

    for (const row of finalRows) {
      process.stdout.write(`${row}\n\n`);
    }

    const terminalWidth = process.stdout.columns ?? 100;
    const dividerWidth = Math.max(
      30,
      Math.min(terminalWidth - 1, 100),
    );

    const divider =
      `\x1b[38;2;100;100;100m` +
      `${'─'.repeat(dividerWidth)}` +
      `\x1b[0m`;

    process.stdout.write(`${divider}\n`);

    process.stdout.write(
      '\x1b[2m  TCS GenAI E2 • Bootcamp Generative AI\x1b[0m\n\n',
    );
  } catch (error) {
    console.error(
      '\n\x1b[31m[Banner] Não foi possível gerar o banner.\x1b[0m',
    );

    console.error(`Detalhes: ${(error as Error).message}\n`);
    process.exitCode = 1;
  }
}

renderBanner();
