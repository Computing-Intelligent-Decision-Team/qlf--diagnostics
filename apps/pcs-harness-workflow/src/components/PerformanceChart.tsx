interface PerformanceChartProps {
  metric: string;
  before: number;
  after: number;
}

const specs: Record<string, { domain: [number, number]; target: number; format: (value: number) => string }> = {
  GBW: { domain: [0, 8_000_000], target: 5_000_000, format: (value) => `${(value / 1e6).toFixed(2)} MHz` },
  gain_db: { domain: [40, 80], target: 60, format: (value) => `${value.toFixed(1)} dB` },
  phase_margin_deg: { domain: [40, 90], target: 60, format: (value) => `${value.toFixed(1)}°` },
  power_w: { domain: [0, .002], target: .001, format: (value) => `${(value * 1e3).toFixed(2)} mW` },
};

export function PerformanceChart({ metric, before, after }: PerformanceChartProps) {
  const spec = specs[metric] ?? { domain: [0, Math.max(before, after, 1)] as [number, number], target: 0, format: (value: number) => value.toPrecision(3) };
  const x = (value: number) => 12 + ((value - spec.domain[0]) / (spec.domain[1] - spec.domain[0])) * 176;
  return (
    <div className="performance-chart" data-testid={`performance-chart-${metric}`} data-domain={spec.domain.join(",")} data-target={spec.target}>
      <div><small>{metric}</small><strong>{spec.format(before)} → {spec.format(after)}</strong></div>
      <svg viewBox="0 0 200 30" aria-label={`${metric} 固定坐标域对比`}>
        <line x1="12" y1="20" x2="188" y2="20" className="chart-axis" />
        <line x1={x(spec.target)} y1="5" x2={x(spec.target)} y2="25" className="target-line" />
        <line x1={x(before)} y1="15" x2={x(after)} y2="15" className="change-line" />
        <circle cx={x(before)} cy="15" r="3.5" className="before-point" />
        <circle cx={x(after)} cy="15" r="3.5" className="after-point" />
      </svg>
    </div>
  );
}
