import { useMemo, useState } from "react";

import type { LayoutVisualization } from "../contracts/physical";

const labels: Record<string, string> = {
  floorplan: "布局边界",
  place: "器件放置",
  route: "路由结果",
  final: "最终版图",
};

const layerColors = ["#43d4b0", "#b8f35a", "#e8b454", "#d66b5c", "#7798e8", "#bd7ee8"];

export function LayoutStage({ data }: { data: LayoutVisualization }) {
  const available = data.checkpoints;
  const [selectedName, setSelectedName] = useState(available.at(-1)?.name ?? "");
  const selected = useMemo(
    () => available.find((checkpoint) => checkpoint.name === selectedName) ?? available.at(-1),
    [available, selectedName],
  );
  if (!selected) return <div className="physical-empty">等待 GDS checkpoint</div>;
  const viewBox = data.view_box.join(" ");
  return (
    <div className="layout-stage">
      <div className="checkpoint-tabs">
        {available.map((checkpoint) => (
          <button
            type="button"
            className={selected.name === checkpoint.name ? "active" : ""}
            key={checkpoint.name}
            onClick={() => setSelectedName(checkpoint.name)}
          >
            <i />{labels[checkpoint.name] ?? checkpoint.name}
          </button>
        ))}
        <span>路由结果逐层展示</span>
      </div>
      <div className="layout-canvas-wrap">
        <svg
          data-testid="layout-canvas"
          data-shared-coordinate-system="true"
          viewBox={viewBox}
          preserveAspectRatio="xMidYMid meet"
          aria-label={`${labels[selected.name] ?? selected.name} GDS 几何`}
        >
          <rect className="layout-grid-bg" x={data.view_box[0]} y={data.view_box[1]} width={data.view_box[2]} height={data.view_box[3]} />
          <g className="gds-reveal" data-checkpoint={selected.name}>
            {selected.shapes.map((shape, index) => {
              const color = layerColors[Math.abs(shape.layer ?? 0) % layerColors.length];
              const common = {
                "data-testid": `gds-shape-${index}`,
                "data-layer": `${shape.layer}/${shape.datatype}`,
                vectorEffect: "non-scaling-stroke" as const,
              };
              return shape.kind === "path" ? (
                <polyline {...common} key={index} points={points(shape.points)} fill="none" stroke={color} strokeWidth={shape.width ?? 1} />
              ) : (
                <polygon {...common} key={index} points={points(shape.points)} fill={color} fillOpacity="0.22" stroke={color} strokeWidth="0.65" />
              );
            })}
            {selected.labels.map((label, index) => label.xy && (
              <text key={index} x={label.xy[0]} y={label.xy[1]} fill="#e6efe9" fontSize="4">{label.text}</text>
            ))}
          </g>
        </svg>
        <div className="layout-provenance" title={selected.source_sha256}>
          <span>LAYER GEOMETRY</span><code>{selected.source_sha256.slice(0, 12)}…</code>
        </div>
      </div>
    </div>
  );
}

function points(value: number[][]) {
  return value.map((point) => point.join(",")).join(" ");
}
