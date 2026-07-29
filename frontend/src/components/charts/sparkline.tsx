// SVG inline, sem biblioteca. Valores `null` interrompem a linha — é assim
// que o burndown mostra "dia ainda não aconteceu" em vez de cair a zero.

function points(values: (number | null)[], width: number, height: number, max: number): string[] {
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const runs: string[] = [];
  let current: string[] = [];
  values.forEach((value, i) => {
    if (value === null) {
      if (current.length) runs.push(current.join(" "));
      current = [];
      return;
    }
    const y = max === 0 ? height : height - (value / max) * height;
    current.push(`${(i * step).toFixed(2)},${y.toFixed(2)}`);
  });
  if (current.length) runs.push(current.join(" "));
  return runs;
}

export function Sparkline({
  values,
  reference,
  label,
  width = 320,
  height = 80,
}: {
  values: (number | null)[];
  /** Série de referência tracejada — a linha ideal do burndown. */
  reference?: (number | null)[];
  label: string;
  width?: number;
  height?: number;
}) {
  const all = [...values, ...(reference ?? [])].filter((v): v is number => v !== null);
  const max = all.length ? Math.max(...all) : 0;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-20"
      role="img"
      aria-label={label}
      preserveAspectRatio="none"
    >
      {reference &&
        points(reference, width, height, max).map((run, i) => (
          <polyline
            key={`ref-${i}`}
            points={run}
            fill="none"
            stroke="var(--color-muted)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      {points(values, width, height, max).map((run, i) => (
        <polyline
          key={`val-${i}`}
          points={run}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
