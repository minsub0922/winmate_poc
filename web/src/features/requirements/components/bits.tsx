/** 작은 표시 부품 — 출처 배지 · 키맨 아바타/점 · 주제 칩 · 완성도 · 가중치 막대. */
import { useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { Icon } from '@/ui';
import type { Gap, Keyman, Source } from '../api';
import { initialOf, kmClass } from '../lib/format';
import { moveBoundary } from '../lib/weights';

/** 출처 배지(§4.6): 파일에서 온 값만. 마우스를 올리면 `{파일 이름} · {위치}` + 원문 근거 */
export function SrcBadge({ source, style, className }: { source?: Source | null; style?: CSSProperties; className?: string }) {
  if (!source || source.kind !== 'file' || !source.file_label) return null;
  const where = [source.file_name, source.locator].filter(Boolean).join(' · ');
  const title = [where, source.quote ? `“${source.quote}”` : ''].filter(Boolean).join('\n');
  return <span className={`rq-src ${className ?? ''}`} style={style} title={title || undefined} data-src={source.file_label}>{source.file_label}</span>;
}

export function KmAvatar({ name, colorIndex, size = 28 }: { name?: string | null; colorIndex: number; size?: number }) {
  return (
    <span className={`rq-avatar ${kmClass(colorIndex)}`} aria-hidden="true"
      style={{ width: size, height: size, fontSize: size <= 20 ? 10.5 : size <= 22 ? 11 : 12.5 }}>{initialOf(name)}</span>
  );
}

export function KmDot({ colorIndex }: { colorIndex: number }) {
  return <span className={`rq-dot ${kmClass(colorIndex)}`} aria-hidden="true" />;
}

/** 주제 칩(필드 이름 · 키맨 이름 + 색 점) */
export function TopicChip({ gap, keymen, label }: { gap?: Gap; keymen?: Keyman[]; label?: string }) {
  const km = gap?.chip_keyman_id ? keymen?.find((k) => k.id === gap.chip_keyman_id) : undefined;
  return (
    <span className="rq-topic" title={label ?? gap?.chip_label}>
      {km && <KmDot colorIndex={km.color_index} />}
      <span className="wm-ellipsis">{label ?? gap?.chip_label}</span>
    </span>
  );
}

export function KeymanTag({ km }: { km: Keyman }) {
  return <span className="rq-topic"><KmDot colorIndex={km.color_index} /><span className="wm-ellipsis">{km.name}</span></span>;
}

/** `완성도` + 막대 + `{p}%` 또는 `{a}% → {b}%` */
export function Completeness({ value, before }: { value: number; before?: number | null }) {
  return (
    <div className="rq-complete" aria-label={before != null ? `완성도 ${before}% → ${value}%` : `완성도 ${value}%`}>
      <span>완성도</span>
      <span className="rq-complete__bar" aria-hidden="true"><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></span>
      {before != null ? <span><s>{before}%</s> → <b>{value}%</b></span> : <b>{value}%</b>}
    </div>
  );
}

export function Arrow() {
  return <span className="rq-arrow" aria-hidden="true"><Icon name="arrowRight" size={14} strokeWidth={2.4} /></span>;
}

export function CheckMark({ size = 14 }: { size?: number }) {
  return <span className="rq-check" aria-hidden="true" style={{ color: 'var(--wm-brand)', display: 'inline-flex' }}><Icon name="check" size={size} strokeWidth={2.6} /></span>;
}

/**
 * 가중치 막대(§4.6). onChange 가 있으면 경계를 끌어 1% 단위로 조정(각 ≥ 5) — 놓을 때 onCommit.
 * 키보드: 경계 손잡이에서 ←/→.
 */
export function WeightBar({ keymen, size = 'lg', onCommit, showPercent = true }: {
  keymen: Keyman[]; size?: 'sm' | 'md' | 'lg'; onCommit?: (weights: number[]) => void; showPercent?: boolean;
}) {
  const bar = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState<number[] | null>(null);
  const drag = useRef<{ i: number; x: number; start: number[] } | null>(null);
  const values = preview ?? keymen.map((k) => k.weight ?? 0);
  const interactive = !!onCommit && keymen.length >= 2;
  let acc = 0;
  const handles: ReactNode[] = [];
  if (interactive) {
    for (let i = 0; i < keymen.length - 1; i++) {
      acc += values[i];
      const left = acc;
      handles.push(
        <button key={i} type="button" className="rq-wbar__handle" style={{ left: `${left}%` }}
          aria-label={`${keymen[i].name || '키맨'} · ${keymen[i + 1].name || '키맨'} 경계`}
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
            drag.current = { i, x: e.clientX, start: values };
          }}
          onPointerMove={(e) => {
            const d = drag.current;
            if (!d || !bar.current) return;
            const pct = ((e.clientX - d.x) / bar.current.getBoundingClientRect().width) * 100;
            setPreview(moveBoundary(d.start, d.i, Math.round(pct)));
          }}
          onPointerUp={() => {
            const d = drag.current;
            drag.current = null;
            if (d && preview && preview.some((v, j) => v !== d.start[j])) onCommit?.(preview);
            setPreview(null);
          }}
          onKeyDown={(e) => {
            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
            e.preventDefault();
            onCommit?.(moveBoundary(values, i, e.key === 'ArrowLeft' ? -1 : 1));
          }} />,
      );
    }
  }
  return (
    <div ref={bar} className={`rq-wbar ${size !== 'lg' ? `rq-wbar--${size}` : ''}`} role="group" aria-label="키맨 가중치 · 경계를 끌어서 조정" data-weights={values.join(',')}>
      {keymen.map((k, i) => (
        <span key={k.id} className={`rq-wbar__seg ${kmClass(k.color_index)}`} style={{ flex: `${Math.max(values[i], 0.5)} 1 0` }} title={`${k.name} ${values[i]}%`}>
          {showPercent ? `${values[i]}%` : values[i]}
        </span>
      ))}
      {handles}
    </div>
  );
}

export function Shim({ w = '62%' }: { w?: string }) {
  return <span className="rq-shim" style={{ width: w, display: 'block' }} />;
}
