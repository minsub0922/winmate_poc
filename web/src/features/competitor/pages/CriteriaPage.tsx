/** CA3C — 비교 기준 바꾸기(§4.12). 끌어서 순서 · 중요도 1~5 · 켜고 끄기 · 직접 추가 · 추천 → `이 기준으로 분석`(모두 고정). */
import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, cx } from '@/ui';
import { errText, putCriteria, startRun, useAnalysis, useCriteria, type CriterionView } from '../api';
import { useCaShell } from '../hooks';
import { Band, BigButton, CaPage, ErrorCol, FootBar, Grip, Head, LoadingCol, Switch } from '../parts';

interface Row { key: string; id?: string | null; name: string; source: CriterionView['source']; source_count?: number | null; importance: number; enabled: boolean; editing?: boolean }

const srcLabel = (r: Row) => r.source === 'requirements' ? '요구' : r.source === 'industry_cases' ? (r.source_count ? `업종 사례 ${r.source_count}건` : '업종 사례')
  : r.source === 'default' ? '기본' : '직접 추가';

export function CriteriaPage() {
  const { id: aid = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const aq = useAnalysis(aid);
  const a = aq.data;
  const cq = useCriteria(aid);
  useCaShell({ aid, title: a?.title, current: 3, added: a?.added_refs });
  const [rows, setRows] = useState<Row[] | null>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [overIdx, setOverIdx] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    if (cq.data && rows === null) {
      setRows(cq.data.items.map((c) => ({ key: c.id, id: c.id, name: c.name, source: c.source, source_count: c.source_count, importance: c.importance, enabled: c.enabled })));
    }
  }, [cq.data, rows]);

  if (aq.isLoading || cq.isLoading || (cq.data && rows === null)) return <LoadingCol lines={6} />;
  if (aq.isError || cq.isError || !a || !rows) return <ErrorCol message="비교 기준을 불러오지 못했어요" onRetry={() => { void cq.refetch(); }} />;

  const onCount = rows.filter((r) => r.enabled && r.name.trim()).length;
  const names = new Set(rows.map((r) => r.name.trim()));
  const sugg = (cq.data?.suggestions ?? []).filter((s) => !names.has(s.name)).slice(0, 2);
  const backTo = a.status === 'analyzing' ? `/competitor/${aid}/run` : a.version ? `/competitor/${aid}/result` : `/competitor/${aid}/candidates`;

  const set = (i: number, patch: Partial<Row>) => setRows((rs) => rs!.map((r, k) => (k === i ? { ...r, ...patch } : r)));
  const move = (from: number, to: number) => setRows((rs) => {
    const list = [...rs!];
    if (to < 0 || to >= list.length || from === to) return list;
    const [x] = list.splice(from, 1);
    list.splice(to, 0, x);
    return list;
  });
  const add = (r: Omit<Row, 'key'>) => setRows((rs) => [...rs!, { ...r, key: `new${++seq.current}` }]);

  function onGripKey(e: KeyboardEvent, i: number) {
    if (e.key === 'ArrowUp') { e.preventDefault(); move(i, i - 1); }
    if (e.key === 'ArrowDown') { e.preventDefault(); move(i, i + 1); }
  }
  function onDrop(e: DragEvent, i: number) {
    e.preventDefault();
    if (drag !== null) move(drag, i);
    setDrag(null);
    setOverIdx(null);
  }

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      const items = rows!.filter((r) => r.name.trim()).map((r, i) => ({
        id: r.id ?? null, name: r.name.trim().slice(0, 20), source: r.source, source_count: r.source_count ?? null, importance: r.importance, order: i, enabled: r.enabled,
      }));
      const out = await putCriteria(aid, items);
      void qc.invalidateQueries({ queryKey: ['ca'] });
      if (!out.job_id) await startRun(aid, a!.version ? 'rejudge' : 'full');
      nav(`/competitor/${aid}/run`);
    } catch (e) {
      setErr(errText(e, '기준을 저장하지 못했어요'));
      setBusy(false);
    }
  }

  return (
    <CaPage>
      <Head kicker="필요할 때" title="무엇을 기준으로 비교할까요?" desc="요구사항에서 뽑은 기준이 위에 있어요. 끄거나 더할 수 있고, 순서는 중요도예요." />
      <div className="ca-sec" style={{ gap: 10 }}>
        <div className="ca-list" role="group" aria-label={`비교 기준 ${rows.length}`}>
          {rows.map((r, i) => (
            <div key={r.key} className={cx('ca-crow', !r.enabled && 'ca-crow--off', drag === i && 'ca-crow--drag', overIdx === i && drag !== i && 'ca-crow--over')}
              onDragOver={(e) => { if (drag !== null) { e.preventDefault(); setOverIdx(i); } }} onDrop={(e) => onDrop(e, i)} data-name={r.name}>
              <button type="button" className="ca-grip" draggable aria-label={`${r.name || '새 기준'} 순서 옮기기 (위 · 아래 화살표)`}
                onDragStart={(e) => { setDrag(i); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', String(i)); }}
                onDragEnd={() => { setDrag(null); setOverIdx(null); }} onKeyDown={(e) => onGripKey(e, i)}>
                <Grip color="currentColor" width={12} height={14} />
              </button>
              <div className="ca-crow__name">
                {r.editing
                  ? <input autoFocus aria-label="기준 이름" placeholder="기준 이름(20자 이내)" maxLength={20} value={r.name}
                    onChange={(e) => set(i, { name: e.target.value })}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.nativeEvent.isComposing) set(i, { editing: false }); if (e.key === 'Escape') setRows((rs) => rs!.filter((_, k) => k !== i)); }}
                    onBlur={() => (r.name.trim() ? set(i, { editing: false }) : setRows((rs) => rs!.filter((_, k) => k !== i)))} />
                  : <span>{r.name}</span>}
                <span className={cx('ca-src', `ca-src--${r.source}`)}>{srcLabel(r)}</span>
              </div>
              <div className="ca-imp" role="group" aria-label={`${r.name} 중요도 ${r.importance} / 5`}>
                {[1, 2, 3, 4, 5].map((lv) => (
                  <button key={lv} type="button" aria-label={`${r.name} 중요도 ${lv}`} aria-pressed={lv === r.importance} data-on={lv <= r.importance}
                    onClick={() => set(i, { importance: lv })} />
                ))}
              </div>
              <span className="ca-crow__num">{r.importance}</span>
              <Switch on={r.enabled} onChange={(v) => set(i, { enabled: v })} label={`${r.name} ${r.enabled ? '끄기' : '켜기'}`} />
            </div>
          ))}
        </div>
        <div className="ca-critadd">
          <button type="button" className="ca-dashbtn" onClick={() => add({ name: '', source: 'user', importance: 3, enabled: true, editing: true })}>
            <Icon name="plus" size={13} strokeWidth={2.4} />기준 직접 추가
          </button>
          {sugg.length > 0 && <span className="ca-hint" style={{ marginLeft: 6 }}>추천</span>}
          {sugg.map((s) => (
            <button key={s.name} type="button" className="ca-sugg" aria-label={`추천 기준 ${s.name} 더하기`}
              onClick={() => add({ name: s.name, source: 'industry_cases', source_count: s.n || null, importance: 3, enabled: true })}>
              <b>+</b>{s.name}{s.n ? <small>업종 사례 {s.n}건</small> : null}
            </button>
          ))}
        </div>
      </div>
      {err && <Band tone="danger">{err}</Band>}
      <FootBar back={{ to: backTo }}>
        <span className="ca-sel">켜진 기준 <b>{onCount}</b> / {rows.length}</span>
        <BigButton onClick={save} loading={busy} disabled={onCount === 0} disabledReason="켜진 기준이 없어요">이 기준으로 분석</BigButton>
      </FootBar>
    </CaPage>
  );
}

export default CriteriaPage;
