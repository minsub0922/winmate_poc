/**
 * 연결된 가치 전체 보기(보드 webapp1 VpDetail · VP2_Detail) — 900×720.
 * 그 제품 · 솔루션에 연결된 모든 가치 메시지: 이 제안 · 같은 제품을 쓴 다른 제안(가져오기) · KB 공식 메시지(원문 그대로). 공간 칩으로 거른다.
 */
import { useMemo, useState } from 'react';
import { Modal, PathIcon, Skeleton, cx } from '@/ui';
import { useLinked, type VMDoc, type VMItem } from './api';

export function VpDetailDialog({ open, onClose, doc, item, onImport }: {
  open: boolean; onClose: () => void; doc: VMDoc; item: VMItem; onImport: (b: { from_map: string; value_id: string }) => Promise<unknown>;
}) {
  const q = useLinked(doc.id, open ? item.key : null);
  const [f, setF] = useState('전체');
  const [took, setTook] = useState<Record<string, boolean>>({});
  const d = q.data;
  const spaces = useMemo(() => {
    const s = ['전체'];
    for (const v of [...(d?.here ?? []), ...(d?.other ?? [])]) if (!s.includes(v.space)) s.push(v.space);
    return s;
  }, [d]);
  const ok = (sp: string) => f === '전체' || sp === f;
  const here = (d?.here ?? []).filter((v) => ok(v.space));
  const other = (d?.other ?? []).filter((v) => ok(v.space));
  const official = f === '전체' ? (d?.official ?? []) : [];
  const total = (d?.here.length ?? 0) + (d?.other.length ?? 0);
  const nTook = Object.keys(took).length;
  return (
    <Modal open={open} onClose={onClose} width={900} height={720} ariaLabel={`${item.name} 연결된 가치`}
      title={<span className="vd-title"><span className="vd-ic"><PathIcon d="M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.4 6.7 19.4l1.2-6L3.4 9.3l6-.7z" size={20} color="var(--wm-brand)" /></span>
        <span style={{ display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span style={{ fontSize: 19, fontWeight: 700 }}>{item.name}</span><span className="wm-kindtag">{item.kind === 'solution' ? '솔루션' : '제품'}</span></span>
          <span style={{ fontSize: 12.5, color: 'var(--wm-text-muted)', fontWeight: 400 }}>연결된 가치 {total} · 이 제안 {d?.here.length ?? 0} · 다른 제안 {d?.other.length ?? 0}{(item.spaces ?? []).length ? ` · 공간 ${(item.spaces ?? []).join(' · ')}` : ''}</span>
        </span></span>}
      bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column' }}
      footer={<div style={{ display: 'flex', alignItems: 'center', gap: 10, width: '100%' }}>
        <span style={{ flex: 1, fontSize: 12.5, color: 'var(--wm-text-muted)' }}>{nTook ? `가치 ${nTook}개를 이 제안에 가져왔어요 · 공간 · 요구는 이 제안에 맞게 고칠 수 있어요` : '가치 메시지 · 고객의 니즈 · 연결 요구 · 출처를 한곳에서 봐요'}</span>
        <button type="button" className="wm-btn wm-btn--primary wm-btn--h40" onClick={onClose}>닫기</button>
      </div>}>
      <div className="vd-chips"><span>공간</span>{spaces.map((s) => (
        <button key={s} type="button" aria-pressed={f === s} className={cx('vd-chip', f === s && 'vd-chip--on')} onClick={() => setF(s)}>{s}</button>
      ))}</div>
      <div className="vd-body">
        {q.isLoading && [0, 1, 2].map((i) => <Skeleton key={i} h={62} r={11} />)}
        <div className="vd-gh"><b>이 제안 · {doc.code ?? doc.id}</b><span>{doc.sb_id ? `${doc.sb_id} ${doc.title}` : doc.title}</span></div>
        {!here.length && !q.isLoading && <span className="vd-none">이 공간에 연결된 가치가 없어요</span>}
        {here.map((v) => (
          <div key={v.value_id} className="vd-row">
            <span className="vd-space">{v.space}</span>
            <span className="vd-main"><b>{v.message}</b><span className={cx(!v.need && 'vd-warn')}>{v.need ? `고객의 니즈 · “${v.need}”` : '고객의 니즈 · 아직 없음'}</span></span>
            <span className="vd-meta"><b>{v.req ?? '—'}</b><span>{doc.code ?? doc.id} · 이 제안</span></span>
            <span className="vd-act"><span className={cx('wm-bytag', v.by === 'manual' ? 'wm-bytag--manual' : 'wm-bytag--ai-accepted')}>{v.by === 'manual' ? '직접' : 'AI 추천 · 수락'}</span></span>
          </div>
        ))}
        <div className="vd-gh"><b>다른 제안에 연결된 가치</b><span>같은 제품 · 솔루션을 쓴 다른 Storyboard · 가져오면 이 제안에 복사돼요</span></div>
        {!other.length && !q.isLoading && <span className="vd-none">이 공간에 연결된 가치가 없어요</span>}
        {other.map((v) => {
          const t = !!took[v.value_id];
          return (
            <div key={`${v.map_id}:${v.value_id}`} className="vd-row">
              <span className="vd-space">{v.space}</span>
              <span className="vd-main"><b>{v.message}</b><span className={cx(!v.need && 'vd-warn')}>{v.need ? `고객의 니즈 · “${v.need}”` : '고객의 니즈 · 아직 없음'}</span></span>
              <span className="vd-meta"><b>{v.req ?? '—'}</b><span>{v.map_id} · {v.sb_id ? `${v.sb_id} ` : ''}{v.map_title}</span></span>
              <span className="vd-act"><button type="button" className={cx('vd-take', t && 'vd-take--on')} disabled={t}
                onClick={async () => { await onImport({ from_map: v.map_id, value_id: v.value_id }); setTook((x) => ({ ...x, [v.value_id]: true })); }}>{t ? '가져옴' : '이 제안에 가져오기'}</button></span>
            </div>
          );
        })}
        {!!official.length && <div className="vd-gh"><b>삼성 공식 메시지</b><span>KB 원문 그대로 · 대외 사용 전 확인</span></div>}
        {official.map((m, i) => (
          <div key={i} className="vd-row vd-row--off">
            <span className="vd-space">{m.level === 'tagline' ? '헤드라인' : m.level === 'usp' ? 'USP' : '핵심'}</span>
            <span className="vd-main"><b style={{ fontWeight: 600 }}>{m.text}</b>{m.claim_flag && <span className="vd-warn">수치 · 최상급 표현 — 원문 확인</span>}</span>
            <span className="vd-meta"><span>{m.source_url ? new URL(m.source_url).host.replace(/^www\./, '') : '출처 미상'}</span></span>
            <span className="vd-act">{m.source_url && <a className="vd-take" href={m.source_url} target="_blank" rel="noreferrer">원문 ↗</a>}</span>
          </div>
        ))}
      </div>
    </Modal>
  );
}
