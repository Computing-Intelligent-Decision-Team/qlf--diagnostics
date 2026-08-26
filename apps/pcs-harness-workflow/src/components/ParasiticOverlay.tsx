import type { LayoutVisualization, ParasiticVisualization } from "../contracts/physical";

export function ParasiticOverlay({ layout, overlay }: { layout: LayoutVisualization; overlay: ParasiticVisualization }) {
  const checkpoint = layout.checkpoints.at(-1);
  const viewBox = layout.view_box.join(" ");
  return (
    <div className="parasitic-stage">
      <div className="overlay-heading">
        <div><i /><strong>{overlay.label}</strong></div>
        <span>Top {overlay.selection.top_n} + {overlay.selection.include_output_net}</span>
      </div>
      <div className="layout-canvas-wrap parasitic-canvas">
        <svg viewBox={viewBox} preserveAspectRatio="xMidYMid meet" aria-label="版图寄生覆盖层">
          <g className="layout-underlay">
            {checkpoint?.shapes.map((shape, index) => shape.kind === "polygon" ? (
              <polygon key={index} points={points(shape.points)} fill="#688078" fillOpacity=".12" stroke="#526a63" strokeWidth=".45" vectorEffect="non-scaling-stroke" />
            ) : (
              <polyline key={index} points={points(shape.points)} fill="none" stroke="#526a63" strokeWidth=".45" vectorEffect="non-scaling-stroke" />
            ))}
          </g>
          <g className="ground-caps">
            {overlay.ground_caps.map((cap) => {
              const anchor = cap.anchors[0];
              return anchor && (
                <g key={cap.cap_id} data-testid={`ground-cap-${cap.cap_id}`} data-capacitance-ff={cap.capacitance_ff}>
                  <circle cx={anchor.xy[0]} cy={anchor.xy[1]} r={3 + cap.visual_width} fill="none" stroke="#b8f35a" strokeWidth={cap.visual_width / 2} vectorEffect="non-scaling-stroke" opacity=".8" />
                  <circle cx={anchor.xy[0]} cy={anchor.xy[1]} r="1.4" fill="#b8f35a" />
                </g>
              );
            })}
          </g>
          <g className="coupling-caps">
            {overlay.coupling_caps.map((cap) => {
              const [a, b] = cap.anchors;
              if (!a || !b) return null;
              const midX = (a.xy[0] + b.xy[0]) / 2;
              const midY = Math.min(a.xy[1], b.xy[1]) - Math.max(5, Math.abs(a.xy[0] - b.xy[0]) * .12);
              const provenance = `${cap.cap_id}: ${cap.source_line}; raw PEX SHA-256 ${overlay.source_artifact_sha256}`;
              return (
                <path
                  key={cap.cap_id}
                  data-testid={`coupling-cap-${cap.cap_id}`}
                  data-artifact-sha256={overlay.source_artifact_sha256}
                  d={`M ${a.xy[0]} ${a.xy[1]} Q ${midX} ${midY} ${b.xy[0]} ${b.xy[1]}`}
                  fill="none"
                  stroke="#43d4b0"
                  strokeWidth={cap.visual_width}
                  vectorEffect="non-scaling-stroke"
                  opacity=".72"
                  aria-label={provenance}
                >
                  <title>{provenance}</title>
                </path>
              );
            })}
          </g>
        </svg>
        <div className="cap-legend"><span><i className="halo" />对地寄生</span><span><i className="curve" />耦合寄生</span><span>线宽：log(C)</span></div>
      </div>
      <p className="coordinate-disclosure">{overlay.coordinate_disclosure}</p>
    </div>
  );
}

function points(value: number[][]) {
  return value.map((point) => point.join(",")).join(" ");
}
