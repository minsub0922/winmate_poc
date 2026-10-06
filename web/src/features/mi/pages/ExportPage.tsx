/** MI4 — 내보내기 · 제안서로 보내기 `/mi/:id/export` (§4.14) */
import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Thumb, cx, toast, useConfirm } from '@/ui';
import { useJob } from '@/api/jobs';
import { fileUrl } from '@/api/client';
import {
  ApiError, errText, handoff, patchHandoff, proposalImport, shareAnalysis, slideRequest, startExport, useAnalysis, useExportView,
  type HandoffIn, type SlidePlan,
} from '../api';
import { useLastScreen } from '../hooks';
import { copyText } from '../lib';
import { Agent, BigButton, Dock, ErrorBand, Ic, LoadingCard, MiPage, P, PromptInput, SecButton, Spin, UserBubble, useAid, useMiShell } from '../parts';
import { EvidenceSheet } from './EvidenceSheet';

type Ask = { kind: 'real_names' | 'confidential' | 'overwrite_pinned'; items?: string[] };
type Confirm = NonNullable<HandoffIn['confirm']>;
const FILE_ICON: Record<string, string> = { pdf_report: P.doc, pptx_onepager: P.monitor, xlsx_table: P.table, share: P.link };
const NEXT_ICON: Record<string, string> = { storyboard: P.storyboard, spec: P.doc, scenario: P.scenario };

export function ExportPage() {
  const aid = useAid();
  const nav = useNavigate();
  const qc = useQueryClient();
  const a = useAnalysis(aid);
  useMiShell(a.data, 3, { complete: true });
  useLastScreen(aid, 'export');
  const [targetId, setTargetId] = useState<string | null>(null);
  const ex = useExportView(aid, targetId);
  const v = ex.data;
  const { confirm, dialog } = useConfirm();
  const [off, setOff] = useState<Record<string, boolean>>({});
  const [opts, setOpts] = useState<{ cite_sources: boolean; fix_notes: boolean; link_why: boolean }>({ cite_sources: true, fix_notes: true, link_why: true });
  const [sending, setSending] = useState(false);
  const [pickOpen, setPickOpen] = useState(false);
  const [evOpen, setEvOpen] = useState(false);
  const [fileJob, setFileJob] = useState<{ id: string; key: string } | null>(null);
  const [said, setSaid] = useState<Array<{ q: string; a?: string }>>([]);
  const pickRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pickOpen) return;
    const close = (e: MouseEvent) => { if (!pickRef.current?.contains(e.target as Node)) setPickOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [pickOpen]);

  useJob(fileJob?.id ?? null, { onDone: (j) => {
    setFileJob(null);
    const fid = (j.result as { file_id?: string } | null)?.file_id;
    if (j.status === 'succeeded' && fid) {
      const link = document.createElement('a');
      link.href = `${fileUrl(fid)}?download=1`;
      link.rel = 'noopener';
      link.target = '_blank';
      link.click();
      toast('파일을 만들었어요');
    } else toast(j.error?.message || '파일을 만들지 못했어요');
  } });

  const rows: SlidePlan[] = v?.rows ?? [];
  const on = (r: SlidePlan) => (off[r.id] === undefined ? r.included : !off[r.id]);
  const chosen = rows.filter(on);
  const target = v?.target as { id: string; title: string; status?: string; proposal_type?: string | null } | null | undefined;
  const proposals = (v?.proposals ?? []) as Array<{ id: string; title: string; status?: string }>;
  const quickwin = v?.usage === 'quickwin';
  const fixN = chosen.reduce((s, r) => s + (r.fix_open ?? 0), 0);
  const footer = [`보낼 시트 ${chosen.length}`, opts.cite_sources ? '출처 표기' : null, opts.fix_notes && fixN ? `[확정 필요] ${fixN}건은 노트로` : null].filter(Boolean).join(' · ');

  async function asksDialog(asks: Ask[], prev: Confirm): Promise<Confirm> {
    const c: Confirm = { ...prev };
    for (const k of asks) {
      if (k.kind === 'real_names') {
        c.real_names = await confirm({ title: '경쟁사 실명을 고객 제출물에 넣을까요?', message: '익명 표기가 꺼져 있어요. 이 제안서에 경쟁사 실명이 그대로 들어가요.',
          cancelLabel: '익명으로 보내기', confirmLabel: '실명으로 보내기', tone: 'dark' });
      } else if (k.kind === 'confidential') {
        const items = k.items ?? [];
        const yes = await confirm({ title: '사내 대외비 값이 들어 있어요', message: `${items.length}개 값이 대외비 자료에서 왔어요 — ${items.join(', ')}. 고객 제출물에 넣을까요?`,
          cancelLabel: '빼고 보내기', confirmLabel: '넣어서 보내기', tone: 'dark' });
        c.confidential = yes ? 'include' : 'exclude';
      } else if (k.kind === 'overwrite_pinned') {
        c.overwrite_pinned = await confirm({ title: '고정한 시트를 덮어쓸까요?', message: `제안서에서 고정한 시트 '${(k.items ?? []).join(', ')}'가 있어요.`,
          cancelLabel: '그대로 두기', confirmLabel: '덮어쓰기', tone: 'dark' });
      }
    }
    return c;
  }

  async function send() {
    if (!aid || !target) return;
    setSending(true);
    let conf: Confirm = {};
    try {
      let out;
      for (let i = 0; i < 4; i += 1) {
        try {
          out = await handoff(aid, { target: 'proposal_mi', target_id: target.id, target_title: target.title, sheets: chosen.map((r) => r.id), options: opts,
            confirm: Object.keys(conf).length ? conf : null });
          break;
        } catch (e) {
          if (e instanceof ApiError && e.code === 'ASK_REQUIRED') { conf = await asksDialog(((e.details?.asks ?? []) as Ask[]), conf); continue; }
          throw e;
        }
      }
      if (!out?.handoff_id) return;
      try {
        await proposalImport(target.id, { section_key: out.section_key, via: 'handoff', source: { feature: 'MI', ref_id: aid, version: a.data?.version, handoff_id: out.handoff_id },
          include_keys: out.sheets });
        await patchHandoff(aid, out.handoff_id, { status: 'delivered', target_title: target.title, target_id: target.id });
        void qc.invalidateQueries({ queryKey: ['mi', 'list'] });
        nav(`/proposal/${target.id}/sections/${out.section_key === 'bigMi' ? 'bigMi' : 'mi'}`);
      } catch (e) {
        await patchHandoff(aid, out.handoff_id, { status: 'failed' }).catch(() => undefined);
        toast(`제안서에 보내지 못했어요 · ${errText(e)}`);
      }
    } catch (e) {
      toast(errText(e));
    } finally {
      setSending(false);
    }
  }

  async function file(key: string) {
    if (!aid) return;
    try {
      if (key === 'share') {
        const r = await shareAnalysis(aid);
        const url = r.share_url.startsWith('http') ? r.share_url : `${window.location.origin}${r.share_url}`;
        toast((await copyText(url)) ? '공유 링크를 복사했어요 · 팀원 보기 · 코멘트' : url);
        return;
      }
      const r = await startExport(aid, key as 'pdf_report' | 'pptx_onepager' | 'xlsx_table', 'customer');
      setFileJob({ id: r.job_id, key });
    } catch (e) { toast(errText(e)); }
  }

  async function request(text: string) {
    if (!aid) return;
    const i = said.length;
    setSaid((x) => [...x, { q: text }]);
    try {
      const r = await slideRequest(aid, text);
      if (r.kind === 'layout' && r.sheet_id) { nav(`/mi/${aid}/slides/${r.sheet_id}?requested=${encodeURIComponent(r.requested ?? '')}&text=${encodeURIComponent(text)}`); return; }
      void ex.refetch();
      setSaid((x) => x.map((y, j) => (j === i ? { ...y, a: r.message || (r.kind === 'include' ? '보낼 시트를 바꿨어요' : '요청을 알아듣지 못했어요') } : y)));
    } catch (e) { setSaid((x) => x.map((y, j) => (j === i ? { ...y, a: errText(e) } : y))); }
  }

  return (
    <MiPage dock={
      <Dock title="결과 활용" meta={a.data?.status === 'done' || a.data?.status === 'upd' ? '분석 완료' : '분석 중'} right={<span className="mi-note" data-testid="mi4-footer">{footer}</span>}
        row={
          <div className="mi-dock__row">
            <PromptInput label="보내기 전 요청" placeholder="보내기 전 요청 (예: 경쟁 환경은 포지셔닝 맵으로)" onSend={request} />
            <SecButton to={`/mi/${aid}/result`}>이전</SecButton>
            <BigButton onClick={() => void send()} busy={sending} disabled={!target || !chosen.length || quickwin}
              reason={!target ? '보낼 제안서를 골라 주세요' : quickwin ? '퀵윈 제안서엔 MI 섹션이 없어요' : '보낼 시트를 골라 주세요'} testId="mi4-send">
              제안서에 {chosen.length}시트 보내기
            </BigButton>
          </div>
        } />
    }>
      <Agent text="분석 결과를 어디에 쓸지 골라주세요. 제안서로 보내면 결과 탭마다 맞는 MI 시트에 나눠 넣고, 시트마다 데이터 모양에 맞는 템플릿을 골라 둡니다.">
        {ex.isError && <ErrorBand onRetry={() => void ex.refetch()} />}
        {!v && !ex.isError && <LoadingCard lines={7} />}
        {v && (
          <div className="mi-card" data-testid="mi4-card">
            <div className="mi-xhead">
              <Ic d={P.monitor} size={17} w={2} className="mi-brand" />
              <span className="mi-card__title">제안서 MI 섹션으로</span>
              <span className="mi-grow" />
              <span className="mi-note" style={{ whiteSpace: 'nowrap' }}>보낼 제안서</span>
              <div className="mi-select" ref={pickRef}>
                <button type="button" className="mi-target" aria-haspopup="listbox" aria-expanded={pickOpen} onClick={() => setPickOpen((x) => !x)} data-testid="mi4-target">
                  <Ic d={P.monitor} size={14} w={2} />
                  <span className="mi-target__label">{target ? <><b>{target.title}</b>{target.status ? ` · ${target.status}` : ''}</> : '보낼 제안서 고르기'}</span>
                  <Ic d={P.chevD} size={12} w={2.4} />
                </button>
                {pickOpen && (
                  <div className="mi-menu" role="listbox" aria-label="보낼 제안서" style={{ width: 320 }}>
                    {!proposals.length && <div className="mi-menu__item" style={{ cursor: 'default' }}><small>최근 제안서가 없어요</small></div>}
                    {proposals.map((p) => (
                      <button key={p.id} type="button" role="option" aria-selected={p.id === target?.id} className="mi-menu__item"
                        onClick={() => { setTargetId(p.id); setPickOpen(false); }}>
                        <b className="mi-ell">{p.title}</b><small>{p.status}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Link to={`/proposal/new?link=${aid}`} className="mi-link"><Ic d={P.plus} size={12} w={2.4} />새 제안서로 시작</Link>
            </div>
            {quickwin && v.vp_card ? (
              <div className="mi-vpcard" data-testid="mi4-vp">
                <b>{(v.vp_card as { title?: string }).title}</b>
                <span className="mi-note" style={{ fontSize: 13 }}>{(v.vp_card as { text?: string }).text}</span>
                <span className="mi-note">퀵윈 제안서엔 MI 섹션이 없어 Value Props 재료로 넘겨요.</span>
              </div>
            ) : (
              <>
                <div style={{ padding: '12px 16px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div className="mi-sheets__head">
                    <span className="mi-sheets__title">시트 매핑 미리보기 <span className="mi-sub">· {v.mapping_head}</span></span>
                    <span className="mi-sheets__hint">템플릿은 제안서에서도 바꿀 수 있어요</span>
                  </div>
                  <div className="mi-maps">
                    {rows.map((r) => <MapCard key={r.id} r={r} on={on(r)} onToggle={(x) => setOff((o) => ({ ...o, [r.id]: !x }))} />)}
                  </div>
                </div>
                <div className="mi-xopts">
                  <label className="mi-check"><input type="checkbox" checked={opts.cite_sources} onChange={(e) => setOpts((o) => ({ ...o, cite_sources: e.target.checked }))} />출처를 시트 하단에 표기</label>
                  <label className="mi-check"><input type="checkbox" checked={opts.fix_notes} onChange={(e) => setOpts((o) => ({ ...o, fix_notes: e.target.checked }))} />[확정 필요] 값은 노트로 남기기</label>
                  {v.show_link_why && (
                    <label className="mi-check"><input type="checkbox" checked={opts.link_why} onChange={(e) => setOpts((o) => ({ ...o, link_why: e.target.checked }))} />
                      삼성 강점 {v.strengths_count} → Why Samsung 근거로도 연결</label>
                  )}
                </div>
              </>
            )}
          </div>
        )}
        {v && (
          <div className="mi-xfiles">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600 }}>파일 · 공유</span>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {v.files.map((f) => (
                  <button key={f.key} type="button" className="mi-xfile" onClick={() => void file(f.key)} disabled={!!fileJob} data-testid={`mi4-file-${f.key}`}>
                    {fileJob?.key === f.key ? <Spin size={15} /> : <Ic d={FILE_ICON[f.key] ?? P.doc} size={15} w={2} className="mi-brand" />}
                    <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}><b>{f.label}</b><small>{f.sub}</small></span>
                  </button>
                ))}
              </div>
            </div>
            <div className="mi-xfiles__sep" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600 }}>다른 기능으로 이어가기</span>
              {(v.next_features as Array<{ key: string; tool: string; what: string; route: string }>).map((h) => {
                const inner = (
                  <>
                    <Ic d={NEXT_ICON[h.key] ?? P.arrow} size={15} w={1.9} />
                    <b>{h.tool}</b><span className="mi-next__what">{h.what}</span><Ic d={P.arrow} size={13} w={2.2} className="mi-brand" />
                  </>
                );
                // Storyboard 는 웹이 근거 스냅숏을 올린다(02-storyboard §8.3) — 시트에서 Key Message 를 고른다
                return h.key === 'storyboard'
                  ? <button key={h.key} type="button" className="mi-next" onClick={() => setEvOpen(true)} data-testid="mi4-next-storyboard">{inner}</button>
                  : <Link key={h.key} to={h.route} className="mi-next">{inner}</Link>;
              })}
              {!v.next_features.length && <span className="mi-note">이어갈 데이터가 아직 없어요</span>}
            </div>
          </div>
        )}
      </Agent>
      {said.map((x, i) => (
        <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <UserBubble>{x.q}</UserBubble>
          {x.a && <Agent text={x.a} />}
        </div>
      ))}
      {dialog}
      {evOpen && aid && <EvidenceSheet aid={aid} onClose={() => setEvOpen(false)} />}
    </MiPage>
  );
}

function MapCard({ r, on, onToggle }: { r: SlidePlan; on: boolean; onToggle: (on: boolean) => void }) {
  const st = r.status ?? (r.in_section ? (r.fix_open ? 'warn' : 'ok') : 'add');
  const label = r.status_label || (st === 'warn' ? `[확정 필요] ${r.fix_open}건` : st === 'ok' ? '그대로 들어가요' : '섹션에 없는 시트 · 추가');
  const tab = r.source_label.replace(/^MI 결과 · /, '');
  return (
    <div className="mi-map" data-sheet={r.id} data-status={st} data-testid="mi4-map">
      <label className={cx('mi-map__src', on && 'mi-map__src--on')}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, minWidth: 0 }}>
          <span className="mi-map__tab">MI 결과 · {tab}</span>
          <span className="mi-map__item">{r.item_label || r.sheet_name}</span>
        </div>
        <input type="checkbox" checked={on} aria-label={`${r.item_label || r.sheet_name} 보내기`} onChange={(e) => onToggle(e.target.checked)} />
      </label>
      <div className={cx('mi-map__arrow', on && 'mi-map__arrow--on')}>
        <svg width="14" height="20" viewBox="0 0 14 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 2v15M3 13l4 4 4-4" /></svg>
      </div>
      <div className={cx('mi-map__card', on && 'mi-map__card--on')}>
        <div style={{ width: '100%', height: 68, display: 'flex', justifyContent: 'center' }}><Thumb kind={r.thumb_kind} n={3} code={r.template_code} /></div>
        <div className="mi-row" style={{ gap: 6, width: '100%' }}>
          <span className="mi-num" style={{ fontSize: 11.5, fontWeight: 800, flexShrink: 0 }}>{r.template_code}</span>
          <span className="mi-ell" style={{ fontSize: 11.5, fontWeight: 600 }}>{r.template_name}</span>
        </div>
        <span className="mi-note mi-ell" style={{ width: '100%' }}>시트 · {r.sheet_name}</span>
        <span className={cx('mi-map__st', st === 'ok' && 'mi-map__st--ok', st === 'warn' && 'mi-map__st--warn')}>
          <Ic d={st === 'ok' ? P.ok : st === 'warn' ? P.warn : P.plus} size={12} w={2.4} />{label}
        </span>
      </div>
    </div>
  );
}
