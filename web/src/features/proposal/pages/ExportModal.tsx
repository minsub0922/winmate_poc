/**
 * PR7X — 내보내기 옵션(§4.24, 보드 PR7X, 모달). `GET …/export-options` → `POST …/exports`(202) → 진행 → 파일마다 내려받기.
 * 파일 수 = 형식 수 × 언어 수(「한국어 + 영문」 = 2), 접미사 `_KO` · `_EN`.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { uploadFile } from '@/api/client';
import { Icon, Modal, toast } from '@/ui';
import { getExport, postExport, postMaster, useExportOptions } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';
import type { ExportRecord, ExportRequest } from '../api/types';
import { Bar, ErrorBand, LoadingCard, SegCtl, SpinIcon } from '../components/parts';
import { R } from '../lib/routes';
import { download } from '../lib/useQuickExport';

type Lang = 'ko' | 'en' | 'ko_en';
const RANGE = /^\s*\d{1,3}(\s*[–-]\s*\d{1,3})?(\s*,\s*\d{1,3}(\s*[–-]\s*\d{1,3})?)*\s*$/;
function rangeOk(s: string) {
  if (!RANGE.test(s)) return false;
  return s.split(',').every((part) => { const [a, b] = part.split(/[–-]/).map((x) => Number(x.trim())); return b === undefined || a <= b; });
}

export function ExportModal({ proposalId, open, onClose, initialLang, version }: { proposalId: string; open: boolean; onClose: () => void; initialLang?: Lang | null; version?: number | null }) {
  const nav = useNavigate();
  const oq = useExportOptions(proposalId, version ?? null, open);
  const o = oq.data;
  const [req, setReq] = useState<ExportRequest | null>(null);
  const [rangeErr, setRangeErr] = useState(false);
  const [masters, setMasters] = useState<Array<{ id: string; name: string; desc?: string }>>([]);
  const [job, setJob] = useState<{ jobId: string; exportId: string | null } | null>(null);
  const [done, setDone] = useState<ExportRecord | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const potx = useRef<HTMLInputElement>(null);
  const [masterOpen, setMasterOpen] = useState(false);

  useEffect(() => {
    if (!o || req) return;
    setReq({ ...o.defaults, lang: initialLang ?? o.defaults.lang, version: version ?? o.defaults.version ?? o.version });
    setMasters(o.masters.map((m) => ({ id: m.id, name: m.name, desc: m.desc })));
  }, [o, req, initialLang, version]);

  const ev = useJobEvents(job?.jobId, {
    onDone: async (j) => {
      const cur = job;
      setJob(null);
      if (j.status !== 'succeeded') { setErr(jobErrText(j.error, '파일을 만들지 못했어요. 다시 시도해 주세요')); return; }
      const xid = cur?.exportId ?? (j.result?.export_id as string | undefined);
      if (xid) { try { setDone(await getExport(proposalId, xid)); } catch (e) { setErr(errText(e)); } }
    },
  });

  const langs: Array<'KO' | 'EN'> = req?.lang === 'ko_en' ? ['KO', 'EN'] : req?.lang === 'en' ? ['EN'] : ['KO'];
  const files = useMemo(() => {
    if (!req) return [];
    const base = req.filename_base || o?.preview_files?.[0]?.replace(/_(KO|EN)\.(pptx|pdf)$/, '') || '';
    const out: string[] = [];
    for (const l of langs) for (const f of (req.formats ?? [])) out.push(`${base}_${l}.${f}`);
    return out;
  }, [req, langs, o?.preview_files]);

  if (!open) return null;
  const set = (patch: Partial<ExportRequest>) => setReq((r) => (r ? { ...r, ...patch } : r));
  const toggleFmt = (f: 'pptx' | 'pdf') => {
    if (!req) return;
    const cur = req.formats ?? [];
    const next = cur.includes(f) ? cur.filter((x) => x !== f) : [...cur, f];
    if (next.length) set({ formats: next });
  };
  const sectionKeyOf = (route: string) => /\/sections\/([^/?]+)/.exec(route)?.[1] ?? route;
  const run = async () => {
    if (!req) return;
    if (req.scope?.kind === 'sheets' && !rangeOk(req.scope.range ?? '')) { setRangeErr(true); return; }
    setErr(null);
    try { const r = await postExport(proposalId, req); setJob({ jobId: r.job_id, exportId: r.export_id ?? null }); } catch (e) { setErr(errText(e)); }
  };
  const onPotx = async (f?: File) => {
    if (!f) return;
    if (!/\.potx$/i.test(f.name)) { toast('.potx 파일만 올릴 수 있어요'); return; }
    try {
      const up = await uploadFile(f, { purpose: 'proposal_master' });
      const m = await postMaster(proposalId, up.id, f.name.replace(/\.potx$/i, ''));
      setMasters((ms) => [...ms, { id: m.master_id, name: m.name, desc: '고객사 템플릿' }]);
      set({ master_id: m.master_id });
    } catch (e) { toast(errText(e)); }
  };
  const curMaster = masters.find((m) => m.id === req?.master_id) ?? masters[0];
  const title = o?.header_label ?? '';

  const footer = done ? (
    <div className="pr-row" style={{ width: '100%' }}>
      <span className="pr-grow pr-note">{(done.team_folder_files?.length ?? 0) > 0 ? `팀 공유 폴더에도 저장했어요 · ${o?.team_folder_path ?? ''}` : '파일을 만들었어요'}</span>
      <button type="button" className="pr-btn pr-btn--h38" onClick={() => nav(R.list())}>목록으로</button>
      <button type="button" className="pr-btn pr-btn--h38 pr-btn--primary" onClick={onClose}>닫기</button>
    </div>
  ) : (
    <div className="pr-row" style={{ width: '100%' }}>
      <span className="pr-grow pr-note" data-testid="pr7x-eta">파일 {files.length}개 · {o?.eta_label?.replace(/^파일 \d+개 · /, '') ?? (langs.includes('EN') ? '영문 변환을 포함해 약 1–2분' : '약 1–2분')}</span>
      <button type="button" className="pr-btn pr-btn--h44" onClick={onClose}>취소</button>
      <button type="button" className="pr-btn pr-btn--primary" onClick={() => void run()} disabled={!req || !!job} data-testid="pr7x-run">
        {job ? <SpinIcon color="currentColor" /> : <Icon name="download" size={15} strokeWidth={2.2} />}내보내기
      </button>
    </div>
  );

  return (
    <Modal open={open} onClose={onClose} ariaLabel="내보내기" width={800} footer={footer}
      title={<span className="pr-row" style={{ gap: 12 }}><span className="pr-iconbox"><Icon name="download" size={16} /></span>
        <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}><span style={{ fontSize: 17, fontWeight: 700 }}>내보내기</span><span className="pr-note" data-testid="pr7x-head">{title}</span></span></span>}>
      {!o || !req ? (oq.isError ? <ErrorBand message={errText(oq.error)} onRetry={() => void oq.refetch()} /> : <LoadingCard lines={6} />) : done ? (
        <div className="pr-colflex" data-testid="pr7x-done">
          <div className="pr-band"><Icon name="check" size={15} color="var(--wm-brand)" strokeWidth={2.8} /><span className="pr-grow">파일 {done.files?.length ?? 0}개를 만들었어요</span></div>
          {(done.files ?? []).map((f) => (
            <div key={f.file_id} className="pr-row" style={{ fontSize: 13 }}>
              <Icon name="file" size={14} color="var(--wm-brand)" /><span className="pr-grow pr-ell">{f.name}</span>
              <button type="button" className="pr-mini" onClick={() => download(f.url, f.name)}>내려받기</button>
            </div>
          ))}
          {(done.warnings ?? []).map((w) => <div key={w} className="pr-note">{w}</div>)}
        </div>
      ) : (
        <div className="pr-colflex" style={{ gap: 18 }} data-testid="pr7x">
          <div className="pr-xp">
            <div>
              <div className="pr-xp__label">형식<small>여러 개 고를 수 있어요</small></div>
              <div className="pr-fmt">
                {(['pptx', 'pdf'] as const).map((f) => (
                  <button key={f} type="button" role="checkbox" aria-checked={(req.formats ?? []).includes(f)} onClick={() => toggleFmt(f)}>
                    <b><input type="checkbox" readOnly checked={(req.formats ?? []).includes(f)} tabIndex={-1} aria-hidden="true" style={{ accentColor: 'var(--wm-brand)', margin: 0 }} />{f.toUpperCase()}</b>
                    <small>{f === 'pptx' ? '편집 가능 · 마스터 유지' : '배포용 · 글꼴 포함'}</small>
                  </button>
                ))}
              </div>
              <div className="pr-xp__label" style={{ marginTop: 18 }}>언어</div>
              <SegCtl label="언어" value={(req.lang ?? 'ko') as Lang} onChange={(l) => set({ lang: l })}
                items={[{ value: 'ko', label: '한국어' }, { value: 'en', label: '영문' }, { value: 'ko_en', label: '한국어 + 영문' }]} />
              <div className="pr-note" style={{ marginTop: 6 }}>{o.tbd_note || '영문은 번역 후 넘치는 문장을 줄이고, [확정 필요] 표시는 [TBD]로 바꿔요.'}</div>
              <div className="pr-xp__label" style={{ marginTop: 18 }}>마스터 템플릿</div>
              <div style={{ position: 'relative' }}>
                <button type="button" className="pr-btn pr-btn--h44" style={{ width: '100%', justifyContent: 'flex-start' }} aria-label="마스터 템플릿 고르기" aria-haspopup="listbox"
                  aria-expanded={masterOpen} onClick={() => setMasterOpen(!masterOpen)}>
                  <span style={{ width: 38, height: 22, borderRadius: 3, border: '1px solid var(--wm-line)', borderTop: '3px solid var(--wm-brand)', flexShrink: 0 }} />
                  <span className="pr-grow pr-ell" style={{ textAlign: 'left' }}>{curMaster?.name}</span>
                  <span className="pr-note">16:9 · 현재 적용</span><Icon name="chevronDown" size={12} />
                </button>
                {masterOpen && (
                  <div className="pr-menu" role="listbox" aria-label="마스터 템플릿" style={{ left: 0, right: 0, top: 48 }}>
                    {masters.map((m) => <button key={m.id} type="button" role="option" aria-selected={m.id === req.master_id} onClick={() => { set({ master_id: m.id }); setMasterOpen(false); }}>{m.name}</button>)}
                  </div>
                )}
              </div>
              <div className="pr-row" style={{ marginTop: 8 }}>
                <input ref={potx} type="file" hidden accept=".potx" onChange={(e) => { void onPotx(e.target.files?.[0]); e.target.value = ''; }} />
                <button type="button" className="pr-logo-btn" style={{ width: 'auto', padding: '0 12px', height: 32 }} onClick={() => potx.current?.click()}><Icon name="upload" size={13} />고객사 템플릿 (.potx) 올리기</button>
                <button type="button" className="pr-link" onClick={() => nav(R.design(proposalId))}>디자인 템플릿 다시 고르기</button>
              </div>
            </div>
            <div>
              <div className="pr-xp__label">범위</div>
              <div className="pr-scope" role="radiogroup" aria-label="범위">
                <button type="button" role="radio" aria-checked={req.scope?.kind !== 'sections' && req.scope?.kind !== 'sheets'} onClick={() => set({ scope: { kind: 'all' } })}>
                  <span className={req.scope?.kind === 'all' || !req.scope?.kind ? 'pr-radio pr-radio--on' : 'pr-radio'} /><b>전체</b><small>시트 {o.sheets_total} + 표지 · 목차</small>
                </button>
                <button type="button" role="radio" aria-checked={req.scope?.kind === 'sections'} onClick={() => set({ scope: { kind: 'sections', section_keys: (o.sections ?? []).map((s) => sectionKeyOf(s.route)) } })}>
                  <span className={req.scope?.kind === 'sections' ? 'pr-radio pr-radio--on' : 'pr-radio'} /><b>섹션 고르기</b><small>{(o.sections ?? []).length}개 섹션 중</small>
                </button>
                {req.scope?.kind === 'sections' && (
                  <div style={{ height: 'auto', flexWrap: 'wrap', padding: '8px 12px', cursor: 'default' }}>
                    {(o.sections ?? []).map((s) => {
                      const k = sectionKeyOf(s.route);
                      const on = (req.scope?.section_keys ?? []).includes(k);
                      return (
                        <label key={k} className="pr-checkline" style={{ width: '50%' }}>
                          <input type="checkbox" checked={on} onChange={() => set({ scope: { kind: 'sections', section_keys: on ? (req.scope?.section_keys ?? []).filter((x) => x !== k) : [...(req.scope?.section_keys ?? []), k] } })} />{s.label}
                        </label>
                      );
                    })}
                  </div>
                )}
                <button type="button" role="radio" aria-checked={req.scope?.kind === 'sheets'} onClick={() => set({ scope: { kind: 'sheets', range: req.scope?.range ?? '' } })}>
                  <span className={req.scope?.kind === 'sheets' ? 'pr-radio pr-radio--on' : 'pr-radio'} /><b>시트 고르기</b><small>예: 01–07, 21</small>
                </button>
                {req.scope?.kind === 'sheets' && (
                  <div style={{ cursor: 'default' }}>
                    <input className="pr-input pr-input--white" style={{ height: 30 }} aria-label="시트 범위" placeholder="01–07, 21" value={req.scope.range ?? ''} aria-invalid={rangeErr || undefined}
                      onChange={(e) => { setRangeErr(false); set({ scope: { kind: 'sheets', range: e.target.value } }); }} data-testid="pr7x-range" />
                  </div>
                )}
              </div>
              {rangeErr && <div role="alert" style={{ fontSize: 11.5, color: 'var(--wm-danger)', marginTop: 4 }}>시트 범위를 확인해 주세요 (예: 01–07, 21)</div>}
              <div className="pr-xp__label" style={{ marginTop: 16 }}>함께 넣기</div>
              {([['speaker_notes', '발표자 노트', ''], ['footnotes', '출처 · 근거 각주', '수치 아래 작게'], ['appendix', '부록', '제품 상세 스펙']] as const).map(([k, l, sub]) => (
                <label key={k} className="pr-checkline">
                  <input type="checkbox" checked={!!req.include?.[k]} onChange={() => set({ include: { ...(req.include ?? { speaker_notes: true, footnotes: true, appendix: false }), [k]: !req.include?.[k] } })} />{l}{sub && <small>{sub}</small>}
                </label>
              ))}
              <div className="pr-note" style={{ margin: '4px 0 10px' }}>{o.include_note || "검토 코멘트와 '추론' 표시는 파일에 넣지 않아요."}</div>
              {o.open_confirm > 0 && (
                <div className="pr-tbd" data-testid="pr7x-tbd">
                  <div className="pr-row pr-row--between"><span style={{ fontSize: 13, fontWeight: 600 }}><Icon name="info" size={13} /> {o.open_confirm_label || `확정 필요 ${o.open_confirm}곳이 남아 있어요`}</span>
                    <button type="button" className="pr-link" onClick={() => nav(R.confirm(proposalId))}>목록 보기</button></div>
                  <SegCtl label="확정 필요 표시" value={req.tbd_mode ?? 'keep_marks'} onChange={(m) => set({ tbd_mode: m })}
                    items={[{ value: 'keep_marks', label: '[확정 필요] 표시 남기기' }, { value: 'move_to_notes', label: '노트로 옮기고 숨기기' }]} />
                </div>
              )}
            </div>
          </div>
          <div>
            <div className="pr-xp__label">파일명
              <span className="pr-row" style={{ gap: 6, fontWeight: 400 }}><small>넣기</small>
                {(o.filename_tokens ?? ['고객사', '제안명', '버전', '날짜']).map((t) => (
                  <button key={t} type="button" className="pr-token" onClick={() => set({ filename_base: `${req.filename_base ?? ''}${req.filename_base ? '_' : ''}{${t}}` })}>{t}</button>
                ))}
              </span>
            </div>
            <div className="pr-fname"><input aria-label="파일명" value={req.filename_base ?? ''} onChange={(e) => set({ filename_base: e.target.value })} data-testid="pr7x-filename" /><span className="pr-note">+ 언어 · 확장자 자동</span></div>
            <div className="pr-row pr-row--wrap" style={{ marginTop: 8, gap: 6 }} data-testid="pr7x-files">
              <span className="pr-note">만들어질 파일 {files.length}개</span>
              {files.map((f) => <span key={f} className="pr-filechip" title={f}>…{f.slice(Math.max(0, f.lastIndexOf('_v') >= 0 ? f.lastIndexOf('_v') : f.length - 14))}</span>)}
            </div>
            <label className="pr-checkline" style={{ marginTop: 10 }}>
              <input type="checkbox" checked={req.team_folder?.enabled !== false} onChange={() => set({ team_folder: { enabled: req.team_folder?.enabled === false, path: req.team_folder?.path ?? null } })} />
              팀 공유 폴더에도 저장 <small>{o.team_folder_path}</small>
            </label>
          </div>
          {job && <div className="pr-colflex"><div className="pr-row" style={{ fontSize: 13 }}><SpinIcon /> 파일을 만드는 중이에요</div><Bar value={ev.progress} label="내보내기 진행률" /></div>}
          {err && <ErrorBand message={err} />}
        </div>
      )}
    </Modal>
  );
}
