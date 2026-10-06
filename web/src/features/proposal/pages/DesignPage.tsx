/**
 * PR6 — 디자인 템플릿(§4.18, 보드 PR6, 5/6). `GET/PUT …/design` · 로고 `POST …/design/logo` · 「PPTX 생성」 `POST …:generate` → PR7.
 * 「이미지 표지」가 켜져 있으면 화면 전체가 이미지 드롭 대상(accepts=image) — 놓은 이미지가 표지 이미지.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { uploadFile } from '@/api/client';
import { Icon, toast, useConfirm, useDropTarget, type DragPayload } from '@/ui';
import { generate, postLogo, putDesign, qk, useDesign, useProposal } from '../api/proposal';
import { errText } from '../api/http';
import type { DesignView } from '../api/types';
import { Agent, Dock, ErrorBand, GhostButton, LoadingCard, NextButton, SegCtl } from '../components/parts';
import { R, normalizeRoute } from '../lib/routes';
import { useProposalShell } from '../lib/useProposalShell';

const HEX = /^#[0-9A-Fa-f]{6}$/;
const DEFAULT_MASTERS: DesignView['masters'] = [
  { id: 'samsung_b2b', name: '삼성 B2B 표준', desc: '화이트 + 삼성 블루 · 16:9 · 사내 표준 마스터', builtin: true, recommended: false, selected: false },
  { id: 'retail_fnb', name: '리테일 · F&B 변형', desc: '이미지 비중 큰 레이아웃 · 매장 사진 강조', builtin: true, recommended: false, selected: false },
  { id: 'simple_white', name: '심플 화이트', desc: '텍스트 중심 · 경영진 보고용', builtin: true, recommended: false, selected: false },
];

const BUILTIN = ['samsung_b2b', 'retail_fnb', 'simple_white'];
/** 마스터 미리보기 — 보드 도식(표준 = 위 블루 띠 · F&B = 왼쪽 검정 면 · 심플 = 회색 바탕) */
function MasterPreview({ i, on, url }: { i: number; on: boolean; url?: string | null }) {
  const radio = <span className={on ? 'pr-master__radio pr-master__radio--on' : 'pr-master__radio'}>{on && <Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} />}</span>;
  if (url) return <div className="pr-master__pv"><img src={url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />{radio}</div>;
  const k = i % 3;
  return (
    <div className={k === 2 ? 'pr-master__pv pr-master__pv--gray' : 'pr-master__pv'} aria-hidden="true">
      {k === 0 && <>
        <i style={{ left: 0, top: 0, right: 0, height: 6, background: 'var(--wm-brand)', borderRadius: 0 }} />
        <i style={{ left: 12, top: 22, width: 120, height: 10, background: 'var(--wm-dark)' }} />
        <i style={{ left: 12, top: 38, width: 80, height: 6, background: 'var(--wm-line-dashed)' }} />
        <i style={{ left: 12, bottom: 12, width: 100, height: 44, background: 'var(--wm-brand-50)', borderRadius: 4 }} />
        <i style={{ left: 122, bottom: 12, width: 100, height: 44, background: 'var(--wm-surface-3)', borderRadius: 4 }} />
      </>}
      {k === 1 && <>
        <i style={{ left: 0, top: 0, bottom: 0, width: 70, background: 'var(--wm-dark)', borderRadius: 0 }} />
        <i style={{ left: 84, top: 22, width: 110, height: 10, background: 'var(--wm-dark)' }} />
        <i style={{ left: 84, top: 38, width: 70, height: 6, background: 'var(--wm-line-dashed)' }} />
        <i style={{ left: 84, bottom: 12, width: 140, height: 44, background: 'var(--wm-surface-3)', borderRadius: 4 }} />
      </>}
      {k === 2 && <>
        <i style={{ left: 12, top: 40, width: 140, height: 12, background: 'var(--wm-dark)' }} />
        <i style={{ left: 12, top: 60, width: 90, height: 6, background: 'var(--wm-line-dashed)' }} />
        <i style={{ left: 12, bottom: 12, width: 40, height: 4, background: 'var(--wm-brand)' }} />
      </>}
      {radio}
    </div>
  );
}

export function DesignPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const pq = useProposal(id);
  const p = pq.data;
  const dq = useDesign(id);
  const dv = dq.data;
  const [hex, setHex] = useState('');
  const [hexErr, setHexErr] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { confirm, dialog } = useConfirm();
  const coverOn = dv?.design.cover?.enabled !== false;
  useProposalShell({ p, step: 5, oneClick: { from: 'design' }, accepts: coverOn ? ['image'] : [], addable: ['image'] });
  useEffect(() => { if (dv?.design && !hex) setHex(dv.design.brand_hex ?? dv.design.color_candidates?.[0] ?? ''); }, [dv?.design, hex]);

  const set = (v: DesignView | null | undefined) => { if (id && v?.design) qc.setQueryData(qk.sub(id, 'design'), v); };
  const save = async (body: Parameters<typeof putDesign>[1], k: string) => {
    if (!id) return;
    setBusy(k);
    try { set(await putDesign(id, body)); } catch (e) { toast(errText(e)); if (k === 'hex') setHexErr(true); } finally { setBusy(null); }
  };
  const drop = useDropTarget({
    accept: ['image'], disabled: !coverOn,
    onDrop: async (pl: DragPayload) => {
      try {
        await save({ cover: { enabled: true, image_ref: { kind: pl.ref.split(':')[1] === 'image' && pl.ref.startsWith('img:') ? 'image_job' : 'kb_image', id: pl.ref, label: pl.label } } }, 'cover');
        toast('표지 이미지로 넣었어요');
        return true;
      } catch { return false; }
    },
  });

  const onLogo = async (f: File | undefined) => {
    if (!f || !id) return;
    if (!/\.(png|svg)$/i.test(f.name) && !/^image\/(png|svg\+xml)$/.test(f.type)) { toast('PNG · SVG만 올릴 수 있어요'); return; }
    if (f.size > 10 * 1024 * 1024) { toast('로고는 10MB까지 올릴 수 있어요'); return; }
    setBusy('logo');
    try { const up = await uploadFile(f, { purpose: 'proposal_logo' }); const v = await postLogo(id, up.id); set(v); setHex(v.design.brand_hex ?? v.design.color_candidates?.[0] ?? hex); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };
  const commitHex = () => {
    if (!HEX.test(hex)) { setHexErr(true); return; }
    setHexErr(false);
    if (hex.toUpperCase() !== (dv?.design.brand_hex ?? '').toUpperCase()) void save({ brand_hex: hex.toUpperCase() }, 'hex');
  };
  const make = async () => {
    if (!id || !dv) return;
    let infer = false;
    const empty = dv.pre_generate?.empty_sections ?? [];
    if (empty.length > 0) {
      const ok = await confirm({
        title: dv.pre_generate?.notice || `자료 없는 시트 ${dv.pre_generate?.empty_sheet_count ?? 0}장 · 딸깍으로 채우기`,
        message: `${empty.map((e) => e.label).join(' · ')} 섹션에 자료가 없어요. 추론으로 채우고 검토가 필요한 곳을 모아 둘게요.`,
        confirmLabel: '추론으로 채우고 만들기', tone: 'dark',
      });
      if (!ok) return;
      infer = true;
    }
    setBusy('generate');
    try { await generate(id, { scope: 'all', infer_empty: infer }); void qc.invalidateQueries({ queryKey: qk.p(id) }); nav(R.result(id)); }
    catch (e) { toast(errText(e)); } finally { setBusy(null); }
  };

  if (pq.isError) return <div className="pr-page"><div className="pr-scroll"><ErrorBand message={errText(pq.error, '제안서를 찾을 수 없어요')} onRetry={() => void pq.refetch()} /></div></div>;
  const masters = dv?.masters?.length ? dv.masters : null;
  const pinned = dv?.sheet_templates?.pinned ?? [];
  const firstPinned = pinned[0] ? p?.sheets?.find((s) => s.sheet_no === pinned[0].sheet_no) : p?.sheets?.[0];
  const lastSection = p?.sections?.filter((s) => s.enabled && !s.hidden).at(-1);
  const colors = dv?.design.color_candidates?.length ? dv.design.color_candidates.slice(0, 3) : ['#1428A0', '#121417'];

  const dock = (
    <Dock title="디자인 템플릿" meta={dv?.header_label?.replace(/^디자인 템플릿 · /, '') || '하나 선택 · 5 / 6'} testId="pr6-dock"
      foot={<>
        <GhostButton to={lastSection ? normalizeRoute(lastSection.route) ?? R.section(p!.id, lastSection.key) : (p ? R.compose(p.id) : '#')}>이전</GhostButton>
        <NextButton onClick={() => void make()} busy={busy === 'generate'} disabled={!dv} testId="pr6-generate">PPTX 생성</NextButton>
      </>}>
      {!dv ? (dq.isError ? <ErrorBand message={errText(dq.error)} onRetry={() => void dq.refetch()} /> : <LoadingCard lines={4} />) : (
        <>
          <div className="pr-masters" role="radiogroup" aria-label="마스터 템플릿">
            {(masters ?? DEFAULT_MASTERS).map((m, i) => {
              const on = (dv.design.master_id ?? 'samsung_b2b') === m.id;
              return (
                <button key={m.id} type="button" role="radio" aria-checked={on} className="pr-master" data-testid={`pr6-master-${i}`}
                  onClick={() => void save({ master_id: m.id }, 'master')} disabled={!!busy}>
                  <MasterPreview i={BUILTIN.indexOf(m.id) >= 0 ? BUILTIN.indexOf(m.id) : i} on={on} url={BUILTIN.includes(m.id) ? null : m.preview_url ?? null} />
                  <span className="pr-row pr-row--between"><span className="pr-master__name">{m.name}</span>{m.recommended && <span className="pr-recpill">추천</span>}</span>
                  <span className="pr-master__desc">{m.desc}</span>
                </button>
              );
            })}
          </div>
          <div className="pr-grid3" style={{ gap: 12, alignItems: 'end' }}>
            <div className="pr-field" style={{ gap: 6 }}>
              <span className="pr-field__label">고객사 로고</span>
              <input ref={fileRef} type="file" hidden accept=".png,.svg,image/png,image/svg+xml" onChange={(e) => { void onLogo(e.target.files?.[0]); e.target.value = ''; }} data-testid="pr6-logo-input" />
              <button type="button" className="pr-logo-btn" onClick={() => fileRef.current?.click()} disabled={busy === 'logo'}>
                {dv.design.logo_file_id ? <><Icon name="check" size={14} strokeWidth={2.6} />로고 바꾸기 (PNG · SVG)</> : <><Icon name="upload" size={14} />로고 업로드 (PNG · SVG)</>}
              </button>
            </div>
            <div className="pr-field" style={{ gap: 6 }}>
              <span className="pr-field__label">고객사 포인트 컬러</span>
              <div className="pr-row" style={{ gap: 6 }}>
                {colors.map((c, i) => (
                  <button key={`${c}-${i}`} type="button" className="pr-swatch" style={{ background: c }} aria-label={`컬러 ${i + 1}`}
                    aria-pressed={(dv.design.brand_hex ?? '').toUpperCase() === c.toUpperCase()} onClick={() => { setHex(c.toUpperCase()); setHexErr(false); void save({ brand_hex: c.toUpperCase() }, 'hex'); }} />
                ))}
                <label htmlFor="pr6-hex" className="wm-sr-only">HEX 입력</label>
                <input id="pr6-hex" className="pr-hex" value={hex} aria-invalid={hexErr || undefined} onChange={(e) => { setHex(e.target.value); setHexErr(false); }}
                  onBlur={commitHex} onKeyDown={(e) => { if (e.key === 'Enter') commitHex(); }} data-testid="pr6-hex" />
              </div>
              {hexErr && <span style={{ fontSize: 11.5, color: 'var(--wm-danger)' }} role="alert">#RRGGBB 형식으로 넣어 주세요</span>}
            </div>
            <div className="pr-field" style={{ gap: 6 }}>
              <span className="pr-field__label">표지 · 옵션</span>
              <div className="pr-row pr-row--wrap" style={{ gap: 6 }}>
                <button type="button" className="pr-toggle" aria-pressed={coverOn} onClick={() => void save({ cover: { enabled: !coverOn, image_ref: dv.design.cover?.image_ref ?? null } }, 'cover')}>이미지 표지</button>
                <button type="button" className="pr-toggle" aria-pressed={dv.design.page_numbers !== false} onClick={() => void save({ page_numbers: !(dv.design.page_numbers !== false) }, 'pn')}>페이지 번호</button>
                <button type="button" className="pr-toggle" aria-pressed={!!dv.design.appendix} onClick={() => void save({ appendix: !dv.design.appendix }, 'apx')}>부록 포함</button>
              </div>
            </div>
          </div>
          <div className="pr-tplline">
            <Icon name="file" size={16} color="var(--wm-brand)" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>시트 템플릿</span>
              <span className="pr-ell" style={{ fontSize: 11.5, color: 'var(--wm-text-muted)' }} data-testid="pr6-templates">
                {dv.sheet_templates?.label || `미리 만든 템플릿 ${dv.sheet_templates?.catalog_total ?? 234}종 (업종별 ${dv.sheet_templates?.industry ?? 75} · 솔루션 전용 ${dv.sheet_templates?.dedicated ?? 54}) · 시트 ${dv.sheet_templates?.sheets_total ?? 0}장 중 직접 고른 ${pinned.length}장${pinned.length ? ` (${pinned.map((x) => x.code).join(' · ')})` : ''} · 나머지 자동 추천`}
              </span>
            </div>
            <SegCtl label="레이아웃 배치 방식" value={dv.design.layout_mode ?? 'auto'} onChange={(m) => void save({ layout_mode: m }, 'layout')}
              items={[{ value: 'auto', label: '자동 추천' }, { value: 'manual', label: '시트마다 직접' }]} />
            {firstPinned && <button type="button" className="pr-link" style={{ fontSize: 12 }} onClick={() => nav(R.template(p!.id, firstPinned.section_key, firstPinned.id))}>시트별로 보기</button>}
          </div>
        </>
      )}
    </Dock>
  );

  return (
    <div className={drop.dragging ? 'pr-page pr-coverdrop' : 'pr-page'} {...drop.props} data-testid="pr6">
      <div className="pr-scroll">
        <div className="pr-col">
          <Agent testId="pr6-agent" text={dv?.intro || '디자인 템플릿을 골라주세요. 사내 표준 템플릿은 업종별 변형이 있고, 고객사 로고와 컬러를 넣으면 표지·섹션 슬라이드에 자동 반영됩니다. 템플릿은 PPTX 마스터 슬라이드로 적용되어 생성 후에도 PowerPoint에서 편집할 수 있습니다.'}>
            {coverOn && dv?.design.cover?.image_ref && (
              <div className="pr-band" data-testid="pr6-cover">
                <Icon name="image" size={15} color="var(--wm-brand)" />
                <span className="pr-grow">표지 이미지 · {dv.design.cover.image_ref.label ?? dv.design.cover.image_ref.id}</span>
                <button type="button" className="pr-mini" onClick={() => void save({ cover: { enabled: true, image_ref: null } }, 'cover')}>빼기</button>
              </div>
            )}
            {coverOn && drop.dragging && <div className="pr-band" style={{ fontWeight: 700, color: 'var(--wm-brand)' }}>여기에 놓아 표지 이미지로 넣기</div>}
          </Agent>
        </div>
      </div>
      {dock}
      {dialog}
    </div>
  );
}
