#!/usr/bin/env node

/**
 * Banner CLI — Bootcamp GenAI E2
 * Estilo inspirado na referência: letras geométricas em blocos,
 * contorno/sombra deslocada e paleta coral/laranja.
 *
 * Instalação:
 *   npm i figlet gradient-string
 *
 * Execução:
 *   node banner.js
 */

const CONFIG = {
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

async function loadDependencies() {
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
    console.error("Execute: npm i figlet gradient-string\n");
    console.error(`Detalhes: ${error.message}`);
    process.exitCode = 1;
    return null;
  }
}

function figletText(figlet, text, font) {
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
        resolve(result);
      },
    );
  });
}

async function createBannerWithFallback(figlet, text) {
  let lastError;

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

function visibleWidth(line) {
  // Remove sequências ANSI antes de calcular a largura visual.
  return line.replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "").length;
}

function joinArtsHorizontally(arts, spacing = 4) {
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

async function renderBanner() {
  const dependencies = await loadDependencies();

  if (!dependencies) {
    return;
  }

  const { figlet, gradient } = dependencies;

  try {
    const renderedTexts = [];

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
    const groupedRows = new Map();

    for (const renderedText of renderedTexts) {
      if (!groupedRows.has(renderedText.row)) {
        groupedRows.set(renderedText.row, []);
      }

      groupedRows.get(renderedText.row).push(renderedText);
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

    console.error(`Detalhes: ${error.message}\n`);
    process.exitCode = 1;
  }
}

renderBanner();
