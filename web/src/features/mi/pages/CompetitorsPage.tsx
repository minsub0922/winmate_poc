/** MI2C — 경쟁사 · 비교 기준 설정 `/mi/:id/competitors` (§4.9) */
import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { cx, toast } from '@/ui';
import {
  addCompetitor, errText, patchAnalysis, patchCompetitor, putCriteria, qk, startRun, useAnalysis, useCompetitors, useCriteria,
  type Competitor, type Criterion,
} from '../api';
import { useLastScreen } from '../hooks';
import { namingLabel, weightPcts } from '../lib';
import { Agent, BigButton, Dock, Ic, MiPage, P, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';

type Crit = Pick<Criterion, 'id' | 'name' | 'source' | 'source_count' | 'weight' | 'enabled' | 'source_label'>;

export function CompetitorsPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 2);
  useLastScreen(aid, 'competitors');
  const [poll, setPoll] = useState<number | false>(false);
  const comps = useCompetitors(aid, poll);
  const crit = useCriteria(aid);
  const [rows, setRows] = useState<Crit[] | null>(null);
  const [name, setName] = useState('');
  const [adding, setAdding] = useState(false);
  const [newCrit, setNewCrit] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState<{ from: number; over: number | null } | null>(null);
  const putTimer = useRef<number | null>(null);

  useEffect(() => { if (crit.data && rows === null) setRows(crit.data.items.map(toCrit)); }, [crit.data, rows]);
  const items = comps.data?.items ?? [];
  useEffect(() => { setPoll(items.some((c) => c.lookup === 'pending') ? 1500 : false); }, [items]);

  const anon = a.data?.anonymize ?? true;
  const mode = (a.data?.naming_mode ?? 'letter') as 'letter' | 'type';

  async function setAnon(next: { anonymize?: boolean; naming_mode?: 'letter' | 'type' }) {
    if (!aid) return;
    try {
      const res = await patchAnalysis(aid, next);
      qc.setQueryData([...qk.analysis(aid), null], res);
      void qc.invalidateQueries({ queryKey: qk.competitors(aid) });
    } catch (e) { toast(errText(e)); }
  }

  async function onAdd(e: KeyboardEvent<HTMLInputElement>) {
    if (e.nativeEvent.isComposing || e.key !== 'Enter' || !aid) return;
    const n = name.trim();
    if (!n) return;
    e.preventDefault();
    setAdding(true);
    try {
      await addCompetitor(aid, n);
      setName('');
      await qc.invalidateQueries({ queryKey: qk.competitors(aid) });
    } catch (err) { toast(errText(err)); } finally { setAdding(false); }
  }

  async function remove(c: Competitor) {
    if (!aid) return;
    try {
      await patchCompetitor(aid, c.id, { removed: true });
      void qc.invalidateQueries({ queryKey: qk.competitors(aid) });
    } catch (e) { toast(errText(e)); }
  }

  function commit(next: Crit[], now = false) {
    setRows(next);
    if (!aid) return;
    if (putTimer.current) window.clearTimeout(putTimer.current);
    const send = async () => {
      try {
        const res = await putCriteria(aid, next.map((c, i) => ({ id: c.id || null, name: c.name, source: c.source, source_count: c.source_count ?? null,
          weight: c.weight, order: i, enabled: c.enabled !== false })));
        qc.setQueryData(qk.criteria(aid), res);
        setRows((cur) => (cur && cur.every((x) => x.id) ? cur : res.items.map(toCrit)));
      } catch (e) {
        toast(errText(e));
        void qc.invalidateQueries({ queryKey: qk.criteria(aid) });
        setRows(null);
      }
    };
    if (now) void send(); else putTimer.current = window.setTimeout(() => void send(), 400);
  }

  const list = rows ?? [];
  const pcts = weightPcts(list.map((c) => c.weight));
  const setWeight = (i: number, w: number) => commit(list.map((c, j) => (j === i ? { ...c, weight: w } : c)));
  const addCrit = (c: Crit) => { if (!list.some((x) => x.name === c.name)) commit([...list, c], true); };
  const sugg = (crit.data?.suggestions ?? []).filter((s) => !list.some((c) => c.name === s.name)).slice(0, 2);

  function onDrop(e: DragEvent, to: number) {
    e.preventDefault();
    if (!drag || drag.from === to) { setDrag(null); return; }
    const next = [...list];
    const [moved] = next.splice(drag.from, 1);
    next.splice(to, 0, moved);
    setDrag(null);
    commit(next, true);
  }

  async function run() {
    if (!aid) return;
    setBusy(true);
    try {
      await startRun(aid, { mode: (a.data?.version ?? 0) > 0 ? 'auto' : 'full' });
      nav(`/mi/${aid}/run`);
    } catch (e) {
      if ((e as { code?: string }).code === 'RUN_IN_PROGRESS') nav(`/mi/${aid}/run`);
      else toast(errText(e));
    } finally { setBusy(false); }
  }

  const memo = [...(a.data?.memos ?? [])].reverse().find((m) => m.where === 'design' || m.where === 'run');
  const counts = comps.data?.counts;
  return (
    <MiPage dock={
      <Dock title="경쟁사 · 비교 기준" meta="경쟁사 분석 → 삼성 강점 · 2 / 3"
        right={<Link to={`/mi/${aid}/scope`} className="mi-link" style={{ height: 28, padding: '0 10px' }}>분석 범위로</Link>}>
        <div className="mi-cc">
          <div className="mi-cc__col">
            <div className="mi-cc__head">
              <b>비교할 경쟁사 <span className="mi-sub">· {items.length}곳</span></b>
              <span>자동 추천 {counts?.auto ?? 0} · 직접 추가 {counts?.user ?? 0}</span>
            </div>
            {items.map((c) => (
              <div key={c.id} className="mi-comp" data-testid="mi2c-comp">
                <span className="mi-comp__letter">{c.letter}</span>
                <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <div className="mi-row" style={{ gap: 6 }}>
                    <span className="mi-comp__label">{namingLabel(c, anon, mode)}</span>
                    {anon && <span className="mi-comp__real" title="작업 안에서만 보여요">{c.real_name}</span>}
                    <span className={cx('mi-tag', c.tag === '자동 추천' && 'mi-tag--brand')}>{c.tag || (c.origin === 'user' ? '직접 추가' : '자동 추천')}</span>
                  </div>
                  <span className="mi-comp__desc">
                    {c.lookup === 'pending' ? <><Spin size={11} /> 유형 · 설명 찾는 중</> : [anon && mode === 'type' ? null : c.kind_label, c.desc].filter(Boolean).join(' · ')}
                  </span>
                </div>
                <button type="button" className="mi-x" aria-label={`경쟁사 ${c.letter} 빼기`} onClick={() => void remove(c)}><Ic d={P.x} size={13} w={2.4} /></button>
              </div>
            ))}
            <div className="mi-addline">
              {adding ? <Spin size={14} /> : <Ic d={P.plus} size={14} w={2.4} />}
              <label htmlFor="mi-comp-add" className="wm-sr-only">경쟁사 추가</label>
              <input id="mi-comp-add" value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => void onAdd(e)} placeholder="경쟁사 추가 (회사명 · 제품명)" />
            </div>
            <div className="mi-anon">
              <div className="mi-row" style={{ gap: 10 }}>
                <button type="button" role="switch" aria-checked={anon} aria-label="제안서에 익명으로 표기" className="mi-switch" onClick={() => void setAnon({ anonymize: !anon })} />
                <span style={{ fontSize: 13, fontWeight: 600 }}>제안서에 익명으로 표기</span>
              </div>
              <span className="mi-note" style={{ fontSize: 11.5 }}>분석에는 실명을 쓰고, 제안서 · PDF · 공유 링크에는 아래 표기로 바꿔요. 경쟁사 로고와 제품 사진은 넣지 않아요.</span>
              <div className="mi-row" role="radiogroup" aria-label="익명 표기 방식" style={{ gap: 6 }}>
                {([['letter', '경쟁사 A · B · C'], ['type', '유형으로 표기']] as const).map(([k, label]) => (
                  <button key={k} type="button" role="radio" aria-checked={anon && mode === k} disabled={!anon} className="mi-naming"
                    onClick={() => void setAnon({ naming_mode: k })}>{label}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="mi-cc__col">
            <div className="mi-cc__head">
              <b>비교 기준 · 가중치</b>
              <span style={{ color: 'var(--wm-text-muted)' }}>끌어서 순서 변경 · 합계 <b className="mi-num" style={{ color: 'var(--wm-text)' }}>100%</b></span>
            </div>
            <div className="mi-crit-list">
              {list.map((c, i) => (
                <div key={c.id || c.name} className={cx('mi-crit', drag?.from === i && 'mi-crit--drag', drag?.over === i && drag.from !== i && 'mi-crit--over')}
                  draggable onDragStart={(e) => { e.dataTransfer.effectAllowed = 'move'; setDrag({ from: i, over: null }); }}
                  onDragOver={(e) => { e.preventDefault(); setDrag((d) => (d ? { ...d, over: i } : d)); }} onDrop={(e) => onDrop(e, i)} onDragEnd={() => setDrag(null)}
                  data-testid="mi2c-crit">
                  <span className="mi-grip" aria-hidden="true"><svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor"><circle cx="3" cy="3" r="1.4" /><circle cx="9" cy="3" r="1.4" /><circle cx="3" cy="7" r="1.4" /><circle cx="9" cy="7" r="1.4" /><circle cx="3" cy="11" r="1.4" /><circle cx="9" cy="11" r="1.4" /></svg></span>
                  <div className="mi-row" style={{ gap: 7 }}>
                    <span className="mi-crit__name" title={c.name}>{c.name}</span>
                    <span className={cx('mi-tag', c.source === 'requirements' && 'mi-tag--brand')} style={{ fontWeight: 600 }}>{c.source_label}</span>
                  </div>
                  <div className="mi-weights" role="group" aria-label={`${c.name} 가중치 ${c.weight} / 5`}>
                    {[1, 2, 3, 4, 5].map((lv) => (
                      <button key={lv} type="button" className={cx('mi-wblock', lv <= c.weight && 'mi-wblock--on')} aria-label={`${c.name} 가중치 ${lv}`} onClick={() => setWeight(i, lv)} />
                    ))}
                  </div>
                  <span className="mi-crit__pct" data-testid="mi2c-pct">{pcts[i]}%</span>
                  <button type="button" className="mi-x" aria-label={`${c.name} 기준 빼기`} onClick={() => commit(list.filter((_, j) => j !== i), true)}><Ic d={P.x} size={11} w={2.4} /></button>
                </div>
              ))}
            </div>
            {newCrit === null
              ? <button type="button" className="mi-addcrit" onClick={() => setNewCrit('')}><Ic d={P.plus} size={13} w={2.4} />기준 직접 추가</button>
              : (
                <div className="mi-addcrit">
                  <Ic d={P.plus} size={13} w={2.4} />
                  <label htmlFor="mi-crit-add" className="wm-sr-only">기준 직접 추가</label>
                  <input id="mi-crit-add" autoFocus value={newCrit} maxLength={40} placeholder="비교 기준 이름" onChange={(e) => setNewCrit(e.target.value)}
                    onBlur={() => { if (!newCrit.trim()) setNewCrit(null); }}
                    onKeyDown={(e) => {
                      if (e.nativeEvent.isComposing) return;
                      if (e.key === 'Escape') setNewCrit(null);
                      if (e.key === 'Enter' && newCrit.trim()) {
                        e.preventDefault();
                        addCrit({ id: '', name: newCrit.trim(), source: 'user', source_count: null, weight: 1, enabled: true, source_label: '직접 추가' });
                        setNewCrit(null);
                      }
                    }} />
                </div>
              )}
            {sugg.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, paddingTop: 2 }}>
                <span className="mi-note" style={{ fontSize: 11.5 }}>{crit.data?.suggestion_head}</span>
                <div className="mi-row" style={{ gap: 6, flexWrap: 'wrap' }}>
                  {sugg.map((s) => (
                    <button key={s.name} type="button" className="mi-sugg" title={s.name}
                      onClick={() => addCrit({ id: '', name: s.name.slice(0, 40), source: 'industry_cases', source_count: s.n, weight: 2, enabled: true, source_label: `업종 사례 ${s.n}건` })}>
                      <i>+</i><span>{s.name}</span><b>{s.n}건</b>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        <div className="mi-dock__row mi-dock__row--between" style={{ paddingTop: 14, gap: 12 }}>
          <span className="mi-note">가중치는 비교표 순서와 강점 도출에만 써요. 경쟁사 수치는 공개 자료로만 채우고, 못 찾으면 [확인 필요]로 남깁니다.</span>
          <div className="mi-row" style={{ gap: 8, flexShrink: 0 }}>
            <SecButton to={`/mi/${aid}/scope`}>이전</SecButton>
            <BigButton onClick={() => void run()} busy={busy} disabled={!list.length && !items.length} testId="mi2c-run">{a.data?.run_label || '분석 시작 (약 3분)'}</BigButton>
          </div>
        </div>
      </Dock>
    }>
      {memo && <UserBubble>{memo.text}</UserBubble>}
      <Agent text={`비교할 경쟁사와 기준을 정리했어요. 가중치가 높은 기준부터 비교표에 놓고, 삼성 강점도 그 순서로 뽑습니다. ${anon ? '제안서와 내보내기에는 경쟁사를 익명으로 표기해요.' : '내부용이라 경쟁사 실명을 그대로 써요.'}`} />
    </MiPage>
  );
}

function toCrit(c: Criterion): Crit {
  return { id: c.id, name: c.name, source: c.source, source_count: c.source_count ?? null, weight: c.weight, enabled: c.enabled, source_label: c.source_label };
}
