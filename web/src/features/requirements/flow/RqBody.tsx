/**
 * 고객 요구사항 본문(보드 webapp1 RQBody — mode saved · editing · new · draft) — ContentDetail 의 cd-body 안을 채운다. px 는 보드 인라인 값 그대로(rqflow.css · 접두어 rqb-).
 *   위: 파일 띠(빈 칸만 채움 · 새로 만들기는 60 점선, 나머지는 46) · 아래: 그리드 340px | 1fr
 *   왼쪽 개요(프로젝트명 · 고객사 · 최종 제안대상 · 제작자 의견) · 오른쪽 키맨별 요구사항(키맨 카드 176px | 1fr · 요구 줄 n · 칸 · 확인 필요 · ×).
 * 칸은 떠날 때 저장(InlineInput). 이 화면에서 고친 칸은 cd-in--chg, 요구 줄은 「고침」/「새로 씀」.
 */
import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type KeyboardEvent, type ReactNode } from 'react';
import { InlineInput } from '@/shell';
import { cx } from '@/ui';
import { MAX_KEYMEN, MAX_REQS, addKeyman, countsOf, emptyReq, marksOf, removeKeyman, type FForm, type FKeyman, type FReq, type Marks } from './form';

const ACCEPT = '.pptx,.pdf,.docx,.txt,.eml,.msg';

type FieldKey = 'title' | 'customer' | 'target';
const FIELDS: Array<{ k: FieldKey; label: string; ph: string; max: number }> = [
  { k: 'title', label: '프로젝트명', ph: '예) 용산 업무시설 재개발', max: 120 },
  { k: 'customer', label: '고객사', ph: '예) E 자산운용', max: 80 },
  { k: 'target', label: '최종 제안대상', ph: '예) 대표이사', max: 80 },
];

/** 고친 칸 꼬리표(보드 RQBody r.chgText: 20 · r999 · brand-50) */
function ChgTag({ mark }: { mark: 'chg' | 'add' | null }) {
  if (!mark) return null;
  return <span className="rqb-tag rqb-tag--chg">{mark === 'add' ? '새로 씀' : '고침'}</span>;
}

/** 가중치 칸(보드 52×28 · Manrope 12.5/800 · 오른쪽 정렬) — 떠날 때 · Enter 에 한 번 저장 */
function WeightInput({ value, onCommit, label, changed, disabled }: { value: number; onCommit: (w: number) => void; label: string; changed: boolean; disabled?: boolean }) {
  const [v, setV] = useState(String(value));
  useEffect(() => { setV(String(value)); }, [value]);
  const commit = () => {
    const n = Math.max(0, Math.min(100, Number(v.replace(/[^0-9]/g, '')) || 0));
    setV(String(n));
    if (n !== value) onCommit(n);
  };
  return (
    <input className={cx('cd-in', 'rqb-w', changed && 'cd-in--chg')} aria-label={label} inputMode="numeric" value={v} disabled={disabled}
      onChange={(e) => setV(e.target.value.replace(/[^0-9]/g, '').slice(0, 3))} onBlur={commit}
      onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') { setV(String(value)); (e.target as HTMLInputElement).blur(); } }} />
  );
}

function XIcon() {
  return <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden><path d="M6 6l12 12M18 6L6 18" /></svg>;
}

function KeymanCard({ k, idx, n, edit, marks, disabled, focusId, setFocusId }: {
  k: FKeyman; idx: number; n: number; edit: (fn: (f: FForm) => FForm) => void; marks: Marks; disabled: boolean;
  focusId: string | null; setFocusId: (id: string | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  // 새 줄 · 앞 줄로 포커스(data-req 로 찾는다)
  useEffect(() => {
    if (!focusId) return;
    const el = box.current?.querySelector<HTMLInputElement>(`[data-req="${focusId}"] input`);
    if (el) { el.focus(); setFocusId(null); }
  }, [focusId, setFocusId, k.reqs]);
  const setKm = (fn: (x: FKeyman) => FKeyman) => edit((f) => ({ ...f, keymen: f.keymen.map((x) => (x.id === k.id ? fn(x) : x)) }));
  const setReq = (rid: string, fn: (r: FReq) => FReq) => setKm((x) => ({ ...x, reqs: x.reqs.map((r) => (r.id === rid ? fn(r) : r)) }));
  const addReq = (after?: string) => {
    if (k.reqs.length >= MAX_REQS) return;
    const nr = emptyReq();
    setKm((x) => {
      const i = after ? x.reqs.findIndex((r) => r.id === after) : -1;
      const reqs = [...x.reqs];
      reqs.splice(i >= 0 ? i + 1 : reqs.length, 0, nr);
      return { ...x, reqs };
    });
    setFocusId(nr.id);
  };
  const removeReq = (rid: string) => {
    const i = k.reqs.findIndex((r) => r.id === rid);
    setKm((x) => ({ ...x, reqs: x.reqs.filter((r) => r.id !== rid) }));
    const prev = k.reqs[i - 1];
    if (prev) setFocusId(prev.id);
  };
  /** 요구 칸 — Enter: 저장하고 아래에 새 줄 · 빈 칸에서 Backspace: 줄 빼기(InlineInput 의 키 처리 뒤에 거품으로 받는다) */
  const rowKeys = (r: FReq) => (e: KeyboardEvent<HTMLSpanElement>) => {
    if (e.nativeEvent.isComposing || disabled || !(e.target instanceof HTMLInputElement)) return;
    const val = e.target.value;
    if (e.key === 'Enter' && val.trim()) addReq(r.id);
    if (e.key === 'Backspace' && !val && k.reqs.length > 1) { e.preventDefault(); removeReq(r.id); }
  };
  const who = k.role.trim() || `키맨 ${idx + 1}`;
  return (
    <div className="rqb-km" data-keyman={k.id} ref={box}>
      <span className="rqb-kmleft">
        <InlineInput className="rqb-name" label={`키맨 ${idx + 1}`} value={k.role} placeholder="키맨 · 예) 대표이사" maxLength={80} disabled={disabled}
          changed={marks.role(k)} onCommit={(v) => setKm((x) => ({ ...x, role: v }))} />
        <span className="rqb-wrow">
          <span className="rqb-wlabel" aria-hidden>가중치</span>
          <WeightInput label={`${who} 가중치(%)`} value={k.weight} changed={marks.weight(k)} disabled={disabled}
            onCommit={(w) => setKm((x) => ({ ...x, weight: w, weight_by: 'manual' }))} />
          <span className="rqb-pct" aria-hidden>%</span>
        </span>
        {n > 1 && !disabled && (
          <button type="button" className="rqb-kmx" aria-label={`${who} 빼기`} title="키맨 빼기"
            onClick={() => edit((f) => ({ ...f, keymen: removeKeyman(f.keymen, k.id) }))}><XIcon /></button>
        )}
      </span>
      <span className="rqb-reqs">
        {k.reqs.map((r, j) => {
          const mark = marks.req(r);
          const check = r.status === 'check';
          return (
            <span key={r.id} className="rqb-req" data-req={r.id} onKeyDown={rowKeys(r)}>
              <span className="rqb-n" aria-hidden>{j + 1}</span>
              <span className="rqb-rin">
                <InlineInput className="rqb-rt" label={`${who} 요구사항 ${j + 1}`} value={r.text} placeholder="요구사항 · 예) 에너지 사용량 20% 절감" maxLength={300}
                  disabled={disabled} changed={!!mark}
                  onCommit={(t) => setReq(r.id, (x) => ({ ...x, text: t, by: 'manual' }))} />
                {!check && !disabled && r.text.trim() && (
                  <button type="button" className="rqb-mark" onClick={() => setReq(r.id, (x) => ({ ...x, flag: 'ask', status: 'check' }))}
                    aria-label={`${who} 요구사항 ${j + 1} 확인 필요로 표시`}>확인 필요</button>
                )}
              </span>
              {check && (
                <button type="button" className="rqb-tag rqb-tag--warn" disabled={disabled}
                  title={r.flag === 'vague' ? '범위가 불명확해요 · 눌러서 확인 필요 풀기' : '눌러서 확인 필요 풀기'}
                  onClick={() => setReq(r.id, (x) => ({ ...x, flag: 'none', status: 'ok' }))}>확인 필요</button>
              )}
              <ChgTag mark={mark} />
              <button type="button" className="rqb-x" aria-label={`빼기 · ${r.text.trim() || '빈 요구사항'}`} disabled={disabled} onClick={() => removeReq(r.id)}><XIcon /></button>
            </span>
          );
        })}
        <button type="button" className="rqb-addreq" disabled={disabled || k.reqs.length >= MAX_REQS} onClick={() => addReq()}>+ 요구사항</button>
      </span>
    </div>
  );
}

export function RqBody({ form, base, edit, mode, disabled, readFrom, readIsSource, onFiles, onPick, fileInput }: {
  form: FForm;
  /** 「이 화면에서 고친 칸」 기준(저장된 문서를 연 때 · 저장 · 되돌리기 한 때) — 저장 전에는 null */
  base: FForm | null;
  edit: (fn: (f: FForm) => FForm) => void;
  mode: 'saved' | 'editing' | 'new' | 'draft';
  disabled: boolean;
  /** 파일 띠 오른쪽 알약(「회의록.pdf에서 읽음」 · 「… 읽는 중」 · 「아직 읽은 자료 없음」 · 「직접 입력」) */
  readFrom: ReactNode;
  readIsSource: boolean;
  onFiles: (files: File[]) => void;
  onPick: () => void;
  fileInput: React.RefObject<HTMLInputElement | null>;
}) {
  const [over, setOver] = useState(false);
  const [focusId, setFocusId] = useState<string | null>(null);
  const marks = marksOf(base, form);
  const c = countsOf(form);
  const isNew = mode === 'new';
  const onDrag = (e: DragEvent, on: boolean) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes('Files')) return;
    e.preventDefault();
    if (!on && e.currentTarget.contains(e.relatedTarget as Node | null)) return;   // 안쪽 요소로 옮겨 갈 때는 그대로
    setOver(on);
  };
  const onDrop = (e: DragEvent) => {
    if (!Array.from(e.dataTransfer?.types ?? []).includes('Files')) return;
    e.preventDefault();
    setOver(false);
    onFiles(Array.from(e.dataTransfer.files ?? []));
  };
  const setField = (k: FieldKey, v: string) => edit((f) => ({ ...f, [k]: v, [`${k}_by`]: v ? 'manual' : null }));
  const fieldMark = (k: FieldKey | 'note'): 'chg' | 'add' | null => (base && marks.field(k) ? (base[k].trim() ? 'chg' : 'add') : null);
  const addKm = () => {
    if (form.keymen.length >= MAX_KEYMEN) return;
    const next = addKeyman(form.keymen);
    edit((f) => ({ ...f, keymen: next }));
    setFocusId(next[next.length - 1].id);
  };
  // 새 키맨 이름 칸으로 포커스
  useEffect(() => {
    if (!focusId) return;
    const el = document.querySelector<HTMLElement>(`[data-keyman="${focusId}"] .rqb-name`);
    if (el) { el.focus(); setFocusId(null); }
  }, [focusId, form.keymen]);

  return (
    <div className="rqb" onDragOver={(e) => onDrag(e, true)} onDragLeave={(e) => onDrag(e, false)} onDrop={onDrop}>
      {/* 파일로 채우기 — 빈 칸만 채우고, 이미 쓴 칸은 덮지 않음 */}
      <div className={cx('rqb-drop', isNew && 'rqb-drop--new', over && 'rqb-drop--over')} data-state={disabled ? 'filling' : over ? 'over' : 'idle'}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--wm-brand)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }} aria-hidden>
          <path d="M12 15V4 M7 9l5-5 5 5 M4 15v5h16v-5" /></svg>
        <span className="rqb-drop__t">{isNew ? '파일을 끌어다 놓으면 빈 칸이 채워져요' : '파일을 더 놓으면 빈 칸만 채워요'} <span>· PPTX · PDF · DOCX · 메일</span></span>
        <span className={cx('rqb-read', readIsSource && 'rqb-read--src')} role={disabled ? 'status' : undefined}>{readFrom}</span>
        <button type="button" className="rqb-attach" onClick={onPick} disabled={disabled}>파일 첨부</button>
        <input ref={fileInput} type="file" multiple accept={ACCEPT} hidden aria-label="파일 첨부"
          onChange={(e: ChangeEvent<HTMLInputElement>) => { const fs = Array.from(e.target.files ?? []); e.target.value = ''; onFiles(fs); }} />
      </div>

      <div className="rqb-grid">
        {/* 개요 */}
        <div className="rqb-card rqb-ov">
          {FIELDS.map((f) => {
            const m = fieldMark(f.k);
            return (
              <label key={f.k} className="rqb-field" data-field={f.k}>
                <span className="rqb-label">{f.label}{m && <ChgTag mark={m} />}</span>
                <InlineInput className={cx('rqb-f', f.k === 'title' && form.title.trim() && 'rqb-f--b')} label={f.label} value={form[f.k]} placeholder={f.ph}
                  maxLength={f.max} disabled={disabled} changed={!!m} onCommit={(v) => setField(f.k, v)} />
              </label>
            );
          })}
          <label className="rqb-field rqb-field--grow" data-field="note">
            <span className="rqb-label">제작자 의견 <small>· 고객 문서에서 빠져요</small>{fieldMark('note') && <ChgTag mark={fieldMark('note')} />}</span>
            <InlineInput multiline className="rqb-note" label="제작자 의견" value={form.note} placeholder="제안 방향 · 강조할 점" maxLength={2000}
              disabled={disabled} changed={!!fieldMark('note')} onCommit={(v) => edit((f) => ({ ...f, note: v }))} />
          </label>
          <span className="rqb-foot">모두 선택 항목이에요 · 비어 있어도 저장돼요</span>
        </div>

        {/* 키맨별 요구사항 */}
        <div className="rqb-card rqb-kmcard">
          <div className="rqb-kmhead">
            <h2>키맨별 요구사항</h2>
            <span className={cx('rqb-sum', c.weight !== 100 && 'rqb-sum--warn')} data-sum={c.weight}>키맨 {c.all} · 요구 {c.reqs} · 가중치 합 {c.weight}%</span>
            <span style={{ flexGrow: 1 }} />
            <button type="button" className="rqb-addkm" disabled={disabled || form.keymen.length >= MAX_KEYMEN} onClick={addKm}>+ 키맨 추가</button>
          </div>
          <div className="rqb-kms">
            {form.keymen.map((k, i) => (
              <KeymanCard key={k.id} k={k} idx={i} n={form.keymen.length} edit={edit} marks={marks} disabled={disabled}
                focusId={focusId} setFocusId={setFocusId} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
