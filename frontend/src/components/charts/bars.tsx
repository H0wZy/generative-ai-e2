// Barras agrupadas em SVG inline — velocity (committed vs completed).

export type BarGroup = { label: string; values: number[] };

export function Bars({
  groups,
  seriesLabels,
  label,
  height = 140,
}: {
  groups: BarGroup[];
  seriesLabels: string[];
  label: string;
  height?: number;
}) {
  const max = Math.max(1, ...groups.flatMap((g) => g.values));
  const width = Math.max(1, groups.length) * 64;
  const groupWidth = width / Math.max(1, groups.length);
  const barWidth = (groupWidth * 0.6) / Math.max(1, seriesLabels.length);
  const plot = height - 20;
  const fills = ["var(--color-accent)", "var(--color-accent-2-600)"];

  return (
    <figure className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-64" role="img" aria-label={label}>
        {groups.map((group, gi) => {
          const originX = gi * groupWidth + groupWidth * 0.2;
          return (
            <g key={group.label}>
              {group.values.map((value, si) => {
                const barHeight = (value / max) * plot;
                return (
                  <rect
                    key={seriesLabels[si]}
                    x={originX + si * barWidth}
                    y={plot - barHeight}
                    width={barWidth - 2}
                    height={barHeight}
                    rx="2"
                    fill={fills[si % fills.length]}
                  />
                );
              })}
              <text
                x={gi * groupWidth + groupWidth / 2}
                y={height - 6}
                textAnchor="middle"
                fontSize="10"
                fill="var(--color-muted)"
              >
                {group.label}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-2 flex gap-4 text-xs text-muted-foreground">
        {seriesLabels.map((name, i) => (
          <span key={name} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2 rounded-sm"
              style={{ background: fills[i % fills.length] }}
            />
            {name}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
