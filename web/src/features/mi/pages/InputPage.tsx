/** MI1(이전 흐름) — 고객 요구사항 `/mi/legacy/new?rq=&sb=` · `/mi/:id/input` (§4.5) */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { BoltIcon, toast } from '@/ui';
import { useFeatureItems } from '@/shell';
import {
  createAnalysis, errText, importStoryboard, patchAnalysis, qk, readStoryboard, startDesign, useAnalysis, useSegments, type Analysis,
} from '../api';
import { useInputEditor, useLastScreen } from '../hooks';
import { Agent, BigButton, Dock, Ic, MiPage, ModeChip, P, Spin, useMiShell } from '../parts';

const ACCEPT = '.pdf,.pptx,.docx,.xlsx,.txt,.eml,.msg,.heic,.png,.jpg,.jpeg';
const SB_DAYS = 14;

export function InputPage() {
  const { id: routeId } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(routeId);
  const ed = useInputEditor(routeId, a.data);
  const aid = ed.id;
  const cur: Analysis | undefined = a.data && a.data.id === aid ? a.data : undefined;
  useMiShell(cur, 1, { ensure: async () => ed.ensureId() });
  useLastScreen(routeId, 'input');
  const segs = useSegments();
  const [files, setFiles] = useState<Array<{ file_id: string; name: string }>>([]);
  const [uploading, setUploading] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [sbDone, setSbDone] = useState<string | null>(null);
  const [sbBusy, setSbBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (cur) setFiles((cur.files ?? []).map((f) => ({ file_id: f.file_id, name: f.name || f.file_id })));
  }, [cur?.id, cur?.files?.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // E4 · E5: `?rq=` 면 작업을 바로 만들고(정의서 스냅숏 · 사용 링크는 서버가), `?sb=` 면 가져오기까지(카드 없이)
  useEffect(() => {
    if (routeId || started.current) return;
    const rq = sp.get('rq');
    const sb = sp.get('sb');
    if (!rq && !sb) return;
    started.current = true;
    void (async () => {
      try {
        const created = await createAnalysis({ links: rq ? { requirements_id: rq } : null });
        qc.setQueryData([...qk.analysis(created.id), null], created);
        let after: Analysis = created;
        if (sb) after = await doImport(created.id, sb) ?? created;
        nav(`/mi/${after.id}/input`, { replace: true });
      } catch (e) {
        toast(errText(e));
      }
    })();
  }, [routeId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Storyboard 가져오기 카드: 14일 안에 수정된 내 Storyboard 중 가장 최근 것(E5 로 들어왔으면 카드 없음)
  const sbItems = useFeatureItems('SB', 5);
  const linkedSb = cur?.links?.storyboard_id ?? null;
  const cutoff = Date.now() - SB_DAYS * 86_400_000;
  const sbCand = !linkedSb && !sp.get('sb')
    ? (sbItems.data?.items ?? []).find((it) => Date.parse(it.updated_at) >= cutoff) ?? null
    : null;

  async function doImport(id: string, sbId: string): Promise<Analysis | null> {
    const sb = await readStoryboard(sbId);
    const res = await importStoryboard(id, {
      storyboard_id: sbId, title: sb.title, customer_name: sb.customer_name,
      requirements: sb.requirements.map((t) => ({ text: t, origin: 'storyboard' as const })), key_messages: sb.key_messages,
    });
    qc.setQueryData([...qk.analysis(id), null], res);
    setSbDone(sb.title);
    return res;
  }

  async function importCard() {
    if (!sbCand) return;
    setSbBusy(true);
    try {
      const id = await ed.ensureId();
      await ed.flush();
      const res = await doImport(id, sbCand.item_id);
      if (res) ed.replace(res);
    } catch (e) {
      toast(errText(e));
    } finally {
      setSbBusy(false);
    }
  }

  async function onFiles(list: FileList | null) {
    if (!list?.length) return;
    const picked = Array.from(list);
    setUploading((u) => [...u, ...picked.map((f) => f.name)]);
    try {
      const id = await ed.ensureId();
      const added: Array<{ file_id: string; name: string }> = [];
      for (const f of picked) {
        try {
          const up = await uploadFile(f, { confidential: true, purpose: 'mi.input' });
          added.push({ file_id: up.id, name: up.name || f.name });
        } catch (e) {
          toast(`${f.name} · ${errText(e)}`);
        }
      }
      if (added.length) {
        const next = [...files, ...added];
        setFiles(next);
        const res = await patchAnalysis(id, { files: next.map((x) => ({ file_id: x.file_id, name: x.name })) });
        qc.setQueryData([...qk.analysis(id), null], res);
      }
    } catch (e) {
      toast(errText(e));
    } finally {
      setUploading((u) => u.filter((n) => !picked.some((f) => f.name === n)));
    }
  }

  async function removeFile(fid: string) {
    const next = files.filter((f) => f.file_id !== fid);
    setFiles(next);
    if (aid) {
      try {
        const res = await patchAnalysis(aid, { file_ids: next.map((f) => f.file_id) });
        qc.setQueryData([...qk.analysis(aid), null], res);
      } catch (e) { toast(errText(e)); }
    }
  }

  async function next() {
    setBusy(true);
    try {
      const id = await ed.flush();
      if (!id) return;
      await startDesign(id);
      void qc.invalidateQueries({ queryKey: qk.design(id) });
      nav(`/mi/${id}/design`);
    } catch (e) {
      toast(errText(e));
    } finally {
      setBusy(false);
    }
  }

  async function pickIndustry() {
    const id = ed.draft.customer_name.trim() || ed.draft.requirements_text.trim() || files.length ? await ed.flush() : aid ?? null;
    nav(id ? `/mi/${id}/industry` : '/mi/legacy/new/industry');
  }

  const hasInput = !!(ed.draft.customer_name.trim() || ed.draft.requirements_text.trim() || files.length || cur?.requirements?.length);
  const seg = cur?.segment;
  const pinned = seg?.mode === 'pin' && seg.code;
  const segShort = pinned ? (segs.data?.items.find((s) => s.code === seg.code)?.short ?? (seg.code === 'GEN' ? '범용' : seg.code)) : null;
  const sbTitle = sbDone ?? (linkedSb ? cur?.links?.storyboard_title ?? null : null);

  return (
    <MiPage gap22 dock={
      <Dock title="고객 요구사항" meta="1 / 3">
        <div className="mi-fields">
          <div className="mi-field">
            <label htmlFor="mi-cust" className="mi-field__label">고객사</label>
            <div className="mi-input">
              <input id="mi-cust" value={ed.draft.customer_name} maxLength={60} placeholder="예) A 커피 프랜차이즈" onChange={(e) => ed.edit('customer_name', e.target.value)} />
            </div>
          </div>
          <div className="mi-field">
            <span className="mi-field__label">업종 <small>· 16개 업종 중 자동 판별</small></span>
            <div className="mi-segbox" data-testid="mi1-segment">
              {pinned
                ? <><ModeChip mode="pin" /><span className="mi-segbox__name">{segShort}</span></>
                : <><span className="mi-mode mi-mode--auto"><BoltIcon size={10} />자동</span><span className="mi-segbox__hint">입력하면 업종과 레이아웃을 알아서 골라요</span></>}
              <button type="button" className="mi-segbox__link mi-link" onClick={() => void pickIndustry()}>직접 고르기</button>
            </div>
          </div>
        </div>
        <div className="mi-textarea">
          <label htmlFor="mi-req" className="wm-sr-only">요구사항 입력</label>
          <textarea id="mi-req" value={ed.draft.requirements_text} maxLength={4000}
            placeholder="해결하려는 과제와 배경 (예: 320개 매장 디지털 메뉴보드 교체, 본사 일괄 관리, 전기료 절감…)"
            onChange={(e) => ed.edit('requirements_text', e.target.value)} />
        </div>
        {(files.length > 0 || uploading.length > 0) && (
          <div className="mi-files" aria-label="첨부 파일">
            {files.map((f) => (
              <span key={f.file_id} className="mi-file" title={f.name}>
                <Ic d={P.file} size={12} w={2} /><span>{f.name}</span>
                <button type="button" aria-label={`${f.name} 빼기`} onClick={() => void removeFile(f.file_id)}><Ic d={P.x} size={11} w={2.4} /></button>
              </span>
            ))}
            {uploading.map((n) => <span key={n} className="mi-file"><Spin size={12} /><span>{n}</span></span>)}
          </div>
        )}
        <div className="mi-dock__row mi-dock__row--between">
          <div className="mi-row" style={{ gap: 6 }}>
            <button type="button" className="mi-attach" aria-label="파일 첨부" onClick={() => fileRef.current?.click()}><Ic d={P.attach} size={16} w={2} /></button>
            <input ref={fileRef} type="file" hidden multiple accept={ACCEPT} data-testid="mi1-file" onChange={(e) => { void onFiles(e.target.files); e.target.value = ''; }} />
            <span className="mi-note" style={{ fontSize: 12.5 }}>RFP · 고객사 IR 자료 첨부 시 분석 정확도가 올라갑니다</span>
          </div>
          <BigButton onClick={() => void next()} disabled={!hasInput} reason="고객사 · 요구사항 · 파일 중 하나를 입력해 주세요" busy={busy || uploading.length > 0}
            testId="mi1-next">다음 · 분석 설계</BigButton>
        </div>
      </Dock>
    }>
      <Agent text="어떤 고객 요구사항을 기준으로 시장을 분석할까요? 고객사와 업종, 해결하려는 과제를 적어주시면 시장·고객사·사용자·경쟁사 관점에서 조사합니다.">
        {sbTitle && (
          <div className="mi-sbcard mi-sbcard--done" data-testid="mi1-sb-done">
            <div className="mi-sbcard__icon"><Ic d={P.storyboard} size={16} w={2} /></div>
            <div className="mi-grow"><div className="mi-sbcard__title">"{sbTitle}" 에서 가져왔어요</div>
              <div className="mi-sbcard__desc">고객 요구사항과 Key Message를 분석 기준으로 씁니다.</div></div>
          </div>
        )}
        {!sbTitle && sbCand && (
          <div className="mi-sbcard" data-testid="mi1-sb-card">
            <div className="mi-sbcard__icon"><Ic d={P.storyboard} size={16} w={2} /></div>
            <div className="mi-grow" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <div className="mi-sbcard__title">Storyboard 작업에서 요구사항을 가져올까요?</div>
              <div className="mi-sbcard__desc">"{sbCand.title}" 의 고객 요구사항과 Key Message를 그대로 사용합니다.</div>
            </div>
            <button type="button" className="mi-mini mi-mini--primary" style={{ height: 32, padding: '0 12px', fontSize: 12.5 }} onClick={() => void importCard()} disabled={sbBusy}>
              {sbBusy ? <Spin size={12} /> : null}가져오기
            </button>
          </div>
        )}
        {cur && (cur.requirements?.length ?? 0) > 0 && !(cur.requirements_text ?? '').trim() && (
          <div className="mi-note">정의서 요구 {cur.requirements.length}개를 기준으로 분석해요.</div>
        )}
        {a.isError && routeId && <div className="mi-note" role="alert">작업을 불러오지 못했어요. <Link to="/mi/legacy">목록으로</Link></div>}
      </Agent>
    </MiPage>
  );
}
