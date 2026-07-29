import type { BurndownSeries } from "@/lib/types";

// Linha ideal tracejada, linha real cheia. Dia futuro chega como `null` e não
// é desenhado — a curva para no hoje em vez de despencar para zero.
export function Burndown({ series, height = 160 }: { series: BurndownSeries; height?: number }) {
  const width = 480;
  const padding = { top: 8, right: 8, bottom: 20, left: 28 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;

  const max = Math.max(1, ...series.ideal, ...series.actual.filter((v): v is number => v !== null));
  const step = series.days.length > 1 ? plotW / (series.days.length - 1) : 0;

  const x = (i: number) => padding.left + i * step;
  const y = (v: number) => padding.top + plotH - (v / max) * plotH;

  const idealPoints = series.ideal.map((v, i) => `${x(i)},${y(v)}`).join(" ");

  // A linha real pode ter buracos se um dia vier nulo no meio — cada trecho
  // contínuo vira um polyline próprio.
  const runs: string[] = [];
  let current: string[] = [];
  series.actual.forEach((value, i) => {
    if (value === null) {
      if (current.length) runs.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${x(i)},${y(value)}`);
  });
  if (current.length) runs.push(current.join(" "));

  const lastLabel = series.days.length - 1;

  return (
    <figure className="overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-80"
        role="img"
        aria-label="Burndown do sprint: linha ideal e pontos restantes por dia"
      >
        <line
          x1={padding.left}
          y1={padding.top + plotH}
          x2={width - padding.right}
          y2={padding.top + plotH}
          stroke="var(--color-divider)"
        />
        <text x={4} y={padding.top + 8} fontSize="10" fill="var(--color-muted)">
          {max}
        </text>
        <text x={4} y={padding.top + plotH} fontSize="10" fill="var(--color-muted)">
          0
        </text>

        <polyline
          points={idealPoints}
          fill="none"
          stroke="var(--color-muted)"
          strokeWidth="1.5"
          strokeDasharray="4 4"
        />
        {runs.map((run, i) => (
          <polyline
            key={i}
            points={run}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="2"
          />
        ))}

        <text x={padding.left} y={height - 4} fontSize="10" fill="var(--color-muted)">
          {series.days[0]?.slice(5)}
        </text>
        <text
          x={width - padding.right}
          y={height - 4}
          fontSize="10"
          textAnchor="end"
          fill="var(--color-muted)"
        >
          {series.days[lastLabel]?.slice(5)}
        </text>
      </svg>
      <figcaption className="mt-2 flex gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-px w-4 border-t border-dashed border-current" />
          Ideal
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-accent-500" />
          Restante
        </span>
      </figcaption>
    </figure>
  );
}
