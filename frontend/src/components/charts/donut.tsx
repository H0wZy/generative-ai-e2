// Donut em SVG inline via stroke-dasharray num único círculo por fatia.

export type Slice = { label: string; value: number };

const FILLS = [
  "var(--color-accent)",
  "var(--color-accent-2-600)",
  "var(--color-neutral-600)",
  "var(--color-accent-800)",
];

export function Donut({
  slices,
  label,
  size = 140,
}: {
  slices: Slice[];
  label: string;
  size?: number;
}) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  const radius = size / 2 - 12;
  const circumference = 2 * Math.PI * radius;
  let consumed = 0;

  return (
    <figure className="flex items-center gap-4">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={label}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          {total === 0 ? (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="var(--color-neutral-800)"
              strokeWidth="16"
            />
          ) : (
            slices.map((slice, i) => {
              const length = (slice.value / total) * circumference;
              const dash = `${length} ${circumference - length}`;
              const offset = -consumed;
              consumed += length;
              return (
                <circle
                  key={slice.label}
                  cx={size / 2}
                  cy={size / 2}
                  r={radius}
                  fill="none"
                  stroke={FILLS[i % FILLS.length]}
                  strokeWidth="16"
                  strokeDasharray={dash}
                  strokeDashoffset={offset}
                />
              );
            })
          )}
        </g>
      </svg>
      <figcaption className="flex flex-col gap-1 text-xs text-muted-foreground">
        {slices.map((slice, i) => (
          <span key={slice.label} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block size-2 rounded-sm"
              style={{ background: FILLS[i % FILLS.length] }}
            />
            {slice.label}
            <span className="text-text tabular-nums">{slice.value}</span>
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
