/** CA1 넣기 · 자유 양식 / CA1R 넣기 · 고객 요구사항에서(§4.4 · §4.10). 입력은 800ms 자동 저장, 읽기는 600ms. */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, uploadFile, unwrap } from '@/api/client';
import { Icon, PathIcon, Spinner, cx, formatDate } from '@/ui';
import { errText, getAnalysis, qk, savedDefinitions, startFind, useAnalysis, type Definition } from '../api';
import { useCaShell, useInputEditor, useParse, type InputMode } from '../hooks';
import { Band, BigButton, CaPage, FootBar, GUIDE, Head, InfoLine, LoadingCol, SlotStrip } from '../parts';

const MAX_TEXT = 2000;
const ICON_FREE = 'M12 20h9 M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z';
const ICON_REQ = 'M6 3h8l5 5v13H6V3z M14 3v5h5 M9 13h7 M9 17h7';

export function InputPage() {
  const { id: routeId } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const server = useAnalysis(routeId);
  const a = server.data;
  const initial: InputMode = sp.get('input') === 'requirements' ? 'requirements' : 'free';
  const ed = useInputEditor(routeId, a, initial);
  const mode: InputMode = sp.get('input') === 'requirements' ? 'requirements' : (sp.get('input') === 'free' ? 'free' : ed.draft.input_mode);
  useCaShell({ aid: ed.id, title: a?.title || '새 분석', current: 1, added: a?.added_refs });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // 서버 작업이 정의서 방식이면 탭도 그쪽으로(주소에 input 이 없을 때)
  useEffect(() => {
    if (a && !sp.get('input') && a.input_mode === 'requirements') {
      const next = new URLSearchParams(sp);
      next.set('input', 'requirements');
      setSp(next, { replace: true });
    }
  }, [a]); // eslint-disable-line react-hooks/exhaustive-deps

  function setMode(m: InputMode) {
    const next = new URLSearchParams(sp);
    if (m === 'requirements') next.set('input', 'requirements'); else next.delete('input');
    setSp(next, { replace: true });
    ed.update({ input_mode: m }, { save: !!ed.id });
  }

  if (routeId && server.isLoading) return <LoadingCol lines={3} />;
  if (routeId && server.isError) return <CaPage><Band tone="danger" action={<Link to="/competitor/legacy" className="ca-linkbtn ca-linkbtn--brand">작업 목록</Link>}>작업을 찾지 못했어요</Band></CaPage>;

  const running = a && (a.status === 'finding' || a.status === 'ask') && a.current_job_id;
  const analyzing = a?.status === 'analyzing';

  async function find(extra?: { requirements_id?: string | null }) {
    setBusy(true);
    setErr(null);
    try {
      if (extra) ed.update({ input_mode: mode, ...extra });
      const aid = await ed.flush();
      if (!aid) throw new Error(ed.saveError || '저장하지 못했어요');
      await startFind(aid);
      qc.setQueryData(qk.analysis(aid), await getAnalysis(aid));     // 다음 화면이 옛 draft 상태를 보고 되돌아오지 않게
      void qc.invalidateQueries({ queryKey: ['ca', 'list'] });
      nav(`/competitor/${aid}/finding`);
    } catch (e) {
      setErr(errText(e, '경쟁사 찾기를 시작하지 못했어요'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <CaPage>
      <Head kicker={mode === 'requirements' ? '넣기 · 고객 요구사항에서' : '넣기 · 자유 양식'} title="어떤 고객의 경쟁사를 찾을까요?"
        desc={mode === 'requirements' ? '고객 요구사항 정의서를 고르거나, 자유 양식으로 적어 주세요.' : '고객 요구사항 정의서를 고르거나, 아래에 자유롭게 적어 주세요.'} />
      <div className="ca-tabs" role="tablist" aria-label="입력 방식">
        <button type="button" role="tab" aria-selected={mode === 'free'} className="ca-tab" onClick={() => setMode('free')}><PathIcon d={ICON_FREE} size={14} />자유 양식</button>
        <button type="button" role="tab" aria-selected={mode === 'requirements'} className="ca-tab" onClick={() => setMode('requirements')}><PathIcon d={ICON_REQ} size={14} />고객 요구사항에서</button>
      </div>
      {running && <Band action={<Link to={`/competitor/${a!.id}/${a!.status === 'ask' ? 'ask' : 'finding'}`} className="ca-linkbtn ca-linkbtn--brand">찾는 화면으로</Link>}>지금 경쟁사를 찾고 있어요 · 다시 찾으면 그 결과를 바꿔요</Band>}
      {analyzing && <Band action={<Link to={`/competitor/${a!.id}/run`} className="ca-linkbtn ca-linkbtn--brand">분석 화면으로</Link>}>분석하는 중이에요 · 끝난 뒤에 다시 찾을 수 있어요</Band>}
      {mode === 'free'
        ? <FreeForm ed={ed} serverSlots={a?.slots ?? null} busy={busy} disabled={!!analyzing} onFind={() => find()} />
        : <ReqForm ed={ed} busy={busy} disabled={!!analyzing} onFind={(rq) => find({ requirements_id: rq })} preferred={sp.get('rq')} />}
      {(err || ed.saveError) && <Band tone="danger">{err || ed.saveError}</Band>}
    </CaPage>
  );
}

type Editor = ReturnType<typeof useInputEditor>;

function FreeForm({ ed, serverSlots, busy, disabled, onFind }: { ed: Editor; serverSlots: import('../api').SlotsView | null; busy: boolean; disabled: boolean; onFind: () => void }) {
  const d = ed.draft;
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(0);
  const [upErr, setUpErr] = useState<string | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const metas = useQueries({
    queries: d.file_ids.filter((f) => !names[f]).map((f) => ({
      queryKey: ['files', 'meta', f], staleTime: 300_000, retry: false,
      queryFn: async () => unwrap(await api.files.GET('/v1/files/{file_id}', { params: { path: { file_id: f } } })),
    })),
  });
  const nameOf = (f: string) => names[f] ?? metas.find((m) => m.data?.id === f)?.data?.name ?? '첨부 파일';
  const readable = d.text.trim().length >= 10 || d.file_ids.length > 0;
  const p = useParse(readable ? { text: d.text, file_ids: d.file_ids } : null);
  const slots = p.data?.slots ?? (readable ? serverSlots : null);
  const canFind = !!(d.text.trim() || d.file_ids.length) && !uploading;

  async function onFiles(files: FileList | null) {
    if (!files?.length) return;
    setUpErr(null);
    for (const f of Array.from(files)) {
      setUploading((n) => n + 1);
      try {
        const meta = await uploadFile(f, { confidential: true, purpose: 'competitor' });
        setNames((m) => ({ ...m, [meta.id]: meta.name }));
        ed.update({ file_ids: [...ed.current().file_ids, meta.id] });
      } catch (e) {
        setUpErr(errText(e, '파일을 올리지 못했어요'));
      } finally {
        setUploading((n) => n - 1);
      }
    }
    if (fileRef.current) fileRef.current.value = '';
  }

  return (
    <>
      <div className="ca-compose">
        <div className="ca-compose__body">
          <label htmlFor="ca-text" className="wm-sr-only">고객 · 사업 설명</label>
          <textarea id="ca-text" placeholder="고객사 · 업종 · 장소 · 제품을 한 문단으로 적어 주세요" value={d.text} maxLength={MAX_TEXT}
            onChange={(e) => ed.update({ text: e.target.value.slice(0, MAX_TEXT) })} />
          {(d.file_ids.length > 0 || uploading > 0) && (
            <div className="ca-compose__files" aria-label="올린 파일">
              {d.file_ids.map((f) => (
                <span key={f} className="ca-file" title={nameOf(f)}>
                  <Icon name="file" size={12} /><span className="ca-ell">{nameOf(f)}</span>
                  <button type="button" aria-label={`${nameOf(f)} 빼기`} onClick={() => ed.update({ file_ids: ed.current().file_ids.filter((x) => x !== f) })}><Icon name="x" size={11} /></button>
                </span>
              ))}
              {uploading > 0 && <span className="ca-file"><Spinner label="올리는 중" />올리는 중</span>}
            </div>
          )}
        </div>
        <div className="ca-compose__foot">
          <div className="ca-row">
            <button type="button" className="ca-filebtn" onClick={() => fileRef.current?.click()}>
              <PathIcon d="M21 12l-8.5 8.5a5 5 0 0 1-7-7L14 5a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L16 7" size={15} color="var(--wm-brand)" />파일 올리기
            </button>
            <input ref={fileRef} type="file" multiple hidden accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.txt,.hwp,.hwpx,.md,.eml"
              onChange={(e) => onFiles(e.target.files)} aria-label="파일 올리기" />
            <span className="ca-filehint ca-ell">{upErr ?? 'RFP · 회의록을 올리면 경쟁사 언급과 평가 기준도 읽어요'}</span>
          </div>
          <div className="ca-row" style={{ flexShrink: 0 }}>
            {d.text.length > MAX_TEXT * 0.8 && <span className="ca-count">{d.text.length} / {MAX_TEXT}</span>}
            <BigButton onClick={onFind} disabled={!canFind || disabled} loading={busy}
              disabledReason={disabled ? '분석하는 중에는 다시 찾을 수 없어요' : '고객 · 사업 설명을 적거나 파일을 올려 주세요'}>경쟁사 찾기</BigButton>
          </div>
        </div>
      </div>
      <SlotStrip label="입력에서 읽은 것" slots={slots} count={p.data?.found_count ?? (slots ? undefined : 0)} loading={p.loading} reading={p.data?.reading_files} />
      {p.data?.degraded && <span className="ca-hint">지금은 사내 자료로만 읽었어요 · 고객사 · 장소는 직접 적어 주면 더 잘 찾아요</span>}
      <InfoLine>{GUIDE}</InfoLine>
    </>
  );
}

function ReqForm({ ed, busy, disabled, onFind, preferred }: { ed: Editor; busy: boolean; disabled: boolean; onFind: (rq: string) => void; preferred: string | null }) {
  const d = ed.draft;
  const defs = useQuery({ queryKey: ['ca', 'ext', 'definitions', preferred ?? ''], queryFn: () => savedDefinitions(preferred), staleTime: 30_000, retry: false });
  const list = defs.data ?? [];
  const selected = d.requirements_id ?? (preferred && list.some((x) => x.id === preferred) ? preferred : list[0]?.id ?? null);
  const p = useParse(selected ? { requirements_id: selected, extra_text: d.extra_text } : null);

  return (
    <>
      <div className="ca-sec">
        <div className="ca-sec__head">
          <span>정의서 고르기 <small>· 저장된 정의서 {defs.data ? list.length : '—'}건</small></span>
          <Link to="/requirements">요구사항 목록<Icon name="chevronRight" size={12} strokeWidth={2.4} /></Link>
        </div>
        <div className="ca-radios" role="radiogroup" aria-label="요구사항 정의서">
          {defs.isLoading && <div className="ca-empty"><Spinner /></div>}
          {defs.isError && <div className="ca-empty">정의서 목록을 불러오지 못했어요</div>}
          {defs.data && !list.length && <div className="ca-empty">저장된 정의서가 없어요 · <Link to="/requirements/new">새 요구사항</Link> 을 먼저 만들거나 자유 양식으로 적어 주세요</div>}
          {list.map((x) => <DefRow key={x.id} x={x} on={x.id === selected} onPick={() => ed.update({ requirements_id: x.id, input_mode: 'requirements' })} />)}
        </div>
      </div>
      <div className="ca-sec">
        <SlotStrip label="정의서에서 채운 것" slots={selected ? p.data?.slots : null} count={p.data?.found_count ?? (selected ? undefined : 0)} loading={p.loading} />
        <span className="ca-hint ca-ell">정의서에 없는 항목은 비어 있음으로 표시돼요 · 아래에 덧붙여도 돼요</span>
      </div>
      <div className="ca-line-input">
        <Icon name="plus" size={14} strokeWidth={2.4} color="var(--wm-text-muted)" />
        <label htmlFor="ca-extra" className="wm-sr-only">덧붙일 내용</label>
        <input id="ca-extra" placeholder="덧붙일 내용 (선택) — 예: 경쟁사로 꼭 넣을 곳, 빼야 할 곳" value={d.extra_text} maxLength={2000}
          onChange={(e) => ed.update({ extra_text: e.target.value, ...(selected && !d.requirements_id ? { requirements_id: selected } : {}) })} />
      </div>
      <InfoLine>{GUIDE}</InfoLine>
      <FootBar back={{ to: '/' }}>
        <BigButton onClick={() => selected && onFind(selected)} disabled={!selected || disabled} loading={busy}
          disabledReason={disabled ? '분석하는 중에는 다시 찾을 수 없어요' : '정의서를 골라 주세요'}>경쟁사 찾기</BigButton>
      </FootBar>
    </>
  );
}

function DefRow({ x, on, onPick }: { x: Definition; on: boolean; onPick: () => void }) {
  const date = x.saved_at ? formatDate(x.saved_at).replaceAll('-', '.') : '';
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (on) ref.current?.scrollIntoView({ block: 'nearest' }); }, [on]);
  return (
    <button ref={ref} type="button" role="radio" aria-checked={on} className={cx('ca-radio')} onClick={onPick}>
      <span className="ca-radio__dot" />
      <span className="ca-radio__name">{x.title || x.project_name || x.customer_name || '이름 없는 정의서'}</span>
      <span className="ca-radio__n">· 요구사항 {x.item_count ?? 0}건</span>
      <span className="ca-radio__date">{date}</span>
    </button>
  );
}

export default InputPage;
