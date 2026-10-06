/** CA4D `출처 · 근거 보기` — 오른쪽 패널(03-mi.md §4.11 MI3S 카드 규칙). 범위 = 이 경쟁사 사실 항목. */
import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { Button, CloseButton, ExternalLink, Icon, Spinner, cx, toast, useEscape, useFocusTrap } from '@/ui';
import { addSource, errText, getClaim, getClaims, qk, removeSource, research, type FactView, type SourceCard } from '../api';

export function EvidencePanel({ aid, cmp, letter, facts, initialFact, onClose }:
  { aid: string; cmp: string; letter: string; facts: FactView[]; initialFact: string | null; onClose: () => void }) {
  const qc = useQueryClient();
  const ref = useRef<HTMLDivElement>(null);
  useFocusTrap(ref, true);
  useEscape(onClose, true);
  const claims = useQuery({ queryKey: qk.claims(aid, { competitor: cmp }), queryFn: () => getClaims(aid, { competitor: cmp }) });
  const items = claims.data?.items ?? [];
  const [sel, setSel] = useState<string | null>(null);
  useEffect(() => {
    if (sel || !items.length) return;
    const first = items.find((c) => !initialFact || c.fact_key === initialFact) ?? items[0];
    setSel(first.id);
  }, [items, sel, initialFact]);
  const detail = useQuery({ queryKey: qk.claim(aid, sel ?? ''), queryFn: () => getClaim(aid, sel!), enabled: !!sel });
  const [url, setUrl] = useState('');
  const [job, setJob] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const refresh = () => { void qc.invalidateQueries({ queryKey: ['ca'] }); };
  useJob(job, { onDone: (j) => { setJob(null); if (j.status === 'failed') setErr(j.error?.message || '출처를 넣지 못했어요'); else toast('출처를 넣었어요'); refresh(); } });

  const current = items.find((c) => c.id === sel);
  const groups = facts.map((f) => ({ f, list: items.filter((c) => c.fact_key === f.key) })).filter((g) => g.list.length);

  async function remove(card: SourceCard) {
    if (!sel) return;
    setBusy(card.source_id);
    setErr(null);
    try {
      await removeSource(aid, sel, card.source_id);
      refresh();
    } catch (e) {
      setErr(errText(e, '출처를 빼지 못했어요'));
    } finally {
      setBusy(null);
    }
  }
  async function copy(card: SourceCard) {
    try {
      await navigator.clipboard.writeText(card.footnote || card.title);
      toast('각주를 복사했어요');
    } catch {
      toast('복사하지 못했어요');
    }
  }
  async function findOther() {
    setBusy('research');
    setErr(null);
    try {
      const r = await research(aid, cmp, current?.fact_key ? [current.fact_key] : null);
      setJob(r.job_id);
      toast('이 항목의 다른 출처를 찾고 있어요');
    } catch (e) {
      setErr(errText(e, '다시 찾지 못했어요'));
    } finally {
      setBusy(null);
    }
  }
  async function addUrl() {
    const u = url.trim();
    if (!/^https?:\/\//.test(u)) { setErr('http(s):// 로 시작하는 주소를 넣어 주세요'); return; }
    setBusy('add');
    setErr(null);
    try {
      const r = await addSource(aid, { url: u, claim_id: sel, competitor_id: cmp, fact_key: (current?.fact_key as FactView['key']) ?? null });
      setUrl('');
      setJob(r.job_id);
    } catch (e) {
      setErr(errText(e, '출처를 넣지 못했어요'));
    } finally {
      setBusy(null);
    }
  }
  async function addFile(files: FileList | null) {
    const f = files?.[0];
    if (!f) return;
    setBusy('file');
    setErr(null);
    try {
      const meta = await uploadFile(f, { confidential: true, purpose: 'competitor' });
      const r = await addSource(aid, { file_id: meta.id, claim_id: sel, competitor_id: cmp, fact_key: (current?.fact_key as FactView['key']) ?? null, classification: 'internal' });
      setJob(r.job_id);
    } catch (e) {
      setErr(errText(e, '사내 문서를 넣지 못했어요'));
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  return (
    <>
      <div className="ca-panel-scrim" onClick={onClose} />
      <aside ref={ref} className="ca-panel" role="dialog" aria-modal="true" aria-label={`경쟁사 ${letter} 출처 · 근거`}>
        <div className="ca-panel__head">
          <h2>경쟁사 {letter} · 출처 · 근거</h2>
          <CloseButton onClick={onClose} />
        </div>
        <div className="ca-panel__body">
          {claims.isLoading && <Spinner />}
          {claims.isError && <span className="ca-adderr">근거를 불러오지 못했어요</span>}
          {claims.data && !items.length && <span className="ca-muted" style={{ fontSize: 13 }}>이 경쟁사는 출처가 붙은 사실이 아직 없어요 · 아래에서 출처를 직접 넣을 수 있어요</span>}
          {groups.map(({ f, list }) => (
            <div key={f.key} className="ca-panel__group">
              <h3>{f.label}</h3>
              {list.map((c) => (
                <button key={c.id} type="button" className="ca-claim" aria-pressed={c.id === sel} onClick={() => setSel(c.id)}>
                  <span className="ca-claim__text">{c.text}</span>
                  {(c.citations?.length ?? 0) > 0 && <span className="ca-sup">{c.citations!.map((x) => x.n).join(',')}</span>}
                  <span className={cx('ca-st', `ca-st--${c.status}`)}>{c.label}</span>
                </button>
              ))}
            </div>
          ))}
          {sel && (
            <div className="ca-panel__group" aria-label="출처 카드">
              <h3>출처</h3>
              {detail.isLoading && <Spinner />}
              {detail.data?.cards.map((card) => (
                <div key={card.source_id} className="ca-scard2" data-kind={card.kind}>
                  <div className="ca-scard2__head">
                    <span className="ca-scard2__n">{card.n || '·'}</span>
                    <span>{card.kind_label}</span>
                    <span className={cx('ca-st', `ca-st--${card.status}`)}>{card.status_label}</span>
                  </div>
                  <div className="ca-scard2__title">{card.title}</div>
                  {card.meta && <div className="ca-hint" style={{ padding: 0 }}>{card.meta}</div>}
                  {card.quote && <blockquote className="ca-scard2__quote"><Quote text={card.quote} hl={card.highlight} /></blockquote>}
                  {card.reason && <div className="ca-scard2__reason">{card.reason}</div>}
                  <div className="ca-scard2__acts">
                    {(card.actions ?? []).includes('원문 열기') && card.url && <ExternalLink href={card.url} arrow className="wm-btn wm-btn--h28">원문 열기</ExternalLink>}
                    {(card.actions ?? []).includes('각주로 복사') && <Button h={28} onClick={() => copy(card)} icon={<Icon name="copy" size={12} />}>각주로 복사</Button>}
                    {(card.actions ?? []).includes('다른 출처 찾기') && <Button h={28} onClick={findOther} loading={busy === 'research'}>다른 출처 찾기</Button>}
                    {(card.actions ?? []).includes('이 출처 빼기') && <Button h={28} variant="ghost" onClick={() => remove(card)} loading={busy === card.source_id}>이 출처 빼기</Button>}
                  </div>
                </div>
              ))}
              {detail.data && !detail.data.cards.length && <span className="ca-muted" style={{ fontSize: 12.5 }}>남은 출처가 없어요 · 이 사실은 [확인 필요] 로 남아요</span>}
            </div>
          )}
          <div className="ca-addsrc">
            <span style={{ fontSize: 12.5, fontWeight: 700 }}>출처 직접 추가 · URL 또는 사내 문서</span>
            <div className="ca-addsrc__row">
              <label htmlFor="ca-src-url" className="wm-sr-only">출처 URL</label>
              <input id="ca-src-url" placeholder="https://" value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void addUrl(); }} />
              <Button h={34} variant="primary" onClick={addUrl} loading={busy === 'add'} disabled={!url.trim()}>넣기</Button>
            </div>
            <div className="ca-row">
              <Button h={32} onClick={() => fileRef.current?.click()} loading={busy === 'file'} icon={<Icon name="upload" size={13} />}>사내 문서 올리기</Button>
              <input ref={fileRef} type="file" hidden onChange={(e) => addFile(e.target.files)} aria-label="사내 문서 올리기" />
              {job && <span className="ca-hint" style={{ padding: 0 }}><Spinner label="넣는 중" /> 원문을 읽고 대조하는 중</span>}
            </div>
            {err && <span className="ca-adderr" role="alert">{err}</span>}
          </div>
        </div>
      </aside>
    </>
  );
}

function Quote({ text, hl }: { text: string; hl?: string | null }) {
  if (!hl) return <>“{text}”</>;
  const i = text.indexOf(hl);
  if (i < 0) return <>“{text}”</>;
  return <>“{text.slice(0, i)}<mark>{hl}</mark>{text.slice(i + hl.length)}”</>;
}

export default EvidencePanel;
