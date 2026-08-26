interface VerificationProps {
  drc: { status: string; count: number | null; artifactHash?: string };
  lvs: { status: string; sourceDevices?: number; extractedDevices?: number; artifactHash?: string };
  pex: { status: string; capacitorCount?: number; artifactHash?: string };
}

export function VerificationPanel({ drc, lvs, pex }: VerificationProps) {
  return (
    <div className="verification-panel" aria-label="物理验证状态">
      <Check name="DRC" status={drc.status} detail={drc.count == null ? "等待规则扫描" : `${drc.count} violations`} hash={drc.artifactHash} />
      <Check
        name="LVS"
        status={lvs.status}
        detail={lvs.sourceDevices == null || lvs.extractedDevices == null ? "等待网表比对" : `${lvs.sourceDevices} source / ${lvs.extractedDevices} extracted`}
        hash={lvs.artifactHash}
      />
      <Check name="PEX" status={pex.status} detail={pex.capacitorCount == null ? "等待寄生提取" : `${pex.capacitorCount} capacitors`} hash={pex.artifactHash} />
    </div>
  );
}

function Check({ name, status, detail, hash }: { name: string; status: string; detail: string; hash?: string }) {
  const good = status === "clean" || status === "completed";
  return (
    <div className={`verification-check ${good ? "good" : status}`} title={hash}>
      <span>{good ? "✓" : status === "failed" || status === "violations" ? "×" : "·"}</span>
      <b>{name}</b><small>{detail}</small>
    </div>
  );
}
