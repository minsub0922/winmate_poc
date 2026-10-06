/** SP3W — 단종 · 값 불일치 경고(`/spec/:id/warnings?w=`, 06-spec §4.11 · §4.17) */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { uploadFile } from '@/api/client';
import { useJob } from '@/api/jobs';
import { PathIcon, cx, toast } from '@/ui';
import {
  addDatasheet, applyWarnings, decideWarning, errText, useSheet, useSheetCache, useWarnings, type Sheet, type Warning,
} from './api';
import { SourcesModal, useFilePicker } from './parts';
import { useRevise } from './revise';
import { Agent, Dock, PromptInput, SpPage, UserBubble, useSpecShell } from './ui';

const TRI = 'M12 3l9.5 17h-19L12 3z M12 10v4.5M12 17.5v.01';
const ROLE: Record<string, string> = { proposed: '제안 모델', existing: '고객 기존 장비', alternative: '대안 모델' };
const GROUP: Record<string, 'discontinued' | 'mismatch' | 'unmet'> = {
  discontinued: 'discontinued', not_in_catalog: 'discontinued', value_mismatch_source: 'mismatch', catalog_changed: 'mismatch',
  value_mismatch_proposal: 'mismatch', requirement_unmet: 'unmet',
};
type Filter = 'all' | 'discontinued' | 'mismatch' | 'unmet';
const STORED = (k: string) => !['find_other', 'upload_datasheet', 'view'].includes(k);

function WarnTable({ s, items, sel, onPick, footer }: { s: Sheet; items: Warning[]; sel: Warning | undefined; onPick: (w: Warning) => void; footer: string }) {
  const t = s.table!;
  const byN = new Map(items.map((w) => [w.n, w]));
  const cols = s.products;
  const disc = new Set(items.filter((w) => w.kind === 'discontinued' || w.kind === 'not_in_catalog').map((w) => w.product_id));
  const hasExisting = cols.some((p) => p.role === 'existing');
  const title = hasExisting ? `${t.title.split(' — ')[0]} — 기존 장비 포함` : t.title;
  return (
    <div className="sp-wt" data-testid="sp-warn-table">
      <div className="sp-wt__head">
        <span className="sp-wt__title">{title}</span>
        <span className="sp-wt__badge"><PathIcon d={TRI} size={12} strokeWidth={2.4} />경고 <span className="sp-numf">{items.length}</span></span>
      </div>
      <div className="sp-wt__cols">
        <span className="sp-wt__k">항목</span>
        {cols.map((p) => {
          const colWarn = (p.warning_ns ?? []).filter((n) => byN.has(n));
          return (
            <span key={p.id} className={cx('sp-wt__col', p.role === 'existing' && 'sp-wt__col--existing')}>
              <span className="sp-wt__name">
                <b>{p.column_label || p.display_name}</b>
                {disc.has(p.id) && <span className="sp-wt__eol">{p.lifecycle?.status === 'discontinued' ? '단종' : '카탈로그 없음'}</span>}
                {colWarn.map((n) => <span key={n} className="sp-wt__n">{n}</span>)}
              </span>
              <span className="sp-wt__role">{ROLE[p.role ?? 'proposed']}</span>
            </span>
          );
        })}
      </div>
      {t.rows.filter((r) => !r.hidden).map((r) => (
        <div key={r.id} className="sp-wt__row">
          <span className="sp-wt__k" title={r.label}>{r.label}</span>
          {(r.cells ?? []).map((c) => {
            const p = cols.find((x) => x.id === c.product_id);
            const ns = (c.warning_ns ?? []).filter((n) => byN.has(n));
            const isSel = !!sel && ns.includes(sel.n);
            const flagged = ns.length > 0;
            return (
              <span key={c.product_id} className={cx('sp-wt__wrap', p?.role === 'existing' && 'sp-wt__wrap--existing')}>
                <span className={cx('sp-wt__cell', flagged && (isSel ? 'sp-wt__cell--sel' : 'sp-wt__cell--flag'), p?.role === 'existing' && 'sp-wt__cell--existing')}
                  data-sel={isSel ? 'true' : undefined} data-flag={flagged ? ns.join(',') : undefined} id={isSel ? 'sp-wsel' : undefined}
                  onClick={flagged ? () => onPick(byN.get(ns[0])!) : undefined} role={flagged ? 'button' : undefined} tabIndex={flagged ? 0 : undefined}
                  onKeyDown={flagged ? (e) => { if (e.key === 'Enter') onPick(byN.get(ns[0])!); } : undefined}>
                  <span className="sp-wt__t">{c.text}</span>
                  {ns.map((n) => <span key={n} className="sp-wt__n sp-wt__n--sm">{n}</span>)}
                </span>
              </span>
            );
          })}
        </div>
      ))}
      <div className="sp-wt__foot">
        <span data-testid="sp-warn-footer">{footer}</span>
        <span className="sp-wt__lg"><span className="sp-wt__lgbox" />번호 = 오른쪽 경고</span>
      </div>
    </div>
  );
}

export default function WarningsPage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const sheetQ = useSheet(id);
  const s = sheetQ.data;
  const wq = useWarnings(id);
  const cache = useSheetCache();
  const revise = useRevise(id, 'warnings');
  const [filter, setFilter] = useState<Filter>('all');
  const [local, setLocal] = useState<Record<string, string>>({});
  const [applying, setApplying] = useState(false);
  const [src, setSrc] = useState<Warning | null>(null);
  const [dsJob, setDsJob] = useState<string | null>(null);
  const dsTarget = useRef<Warning | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useSpecShell(s, 3);
  const items = useMemo(() => wq.data?.items ?? [], [wq.data]);
  const wParam = sp.get('w');
  const sel = items.find((w) => w.id === wParam) ?? items[0];

  // 고른 칸으로 스크롤(경고 카드 · ?w=)
  useEffect(() => {
    const el = document.getElementById('sp-wsel');
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    listRef.current?.querySelector('[data-selected="true"]')?.scrollIntoView({ block: 'nearest' });
  }, [sel?.id]);

  useJob(dsJob, {
    onDone: (j) => {
      setDsJob(null);
      void cache.refresh(id);
      void cache.refreshWarnings(id);
      if (j.status === 'failed') toast(j.error?.message ?? '데이터시트를 읽지 못했어요.');
    },
  });
  const picker = useFilePicker('.pdf,.png,.jpg,.jpeg,.xlsx,.docx', async (f) => {
    const w = dsTarget.current;
    if (!w?.product_id || !s) return;
    try {
      const meta = await uploadFile(f, { confidential: true, purpose: 'sp.datasheet', projectId: s.project_id ?? undefined });
      setDsJob((await addDatasheet(s.id, meta.id, w.product_id)).job_id);
    } catch (e) { toast(errText(e)); }
  });

  if (sheetQ.isError) return <SpPage><Agent text={`작업을 불러오지 못했어요. ${errText(sheetQ.error)}`} /></SpPage>;
  if (!s || !wq.data || !s.table) return <SpPage><div className="sp-note">불러오는 중…</div></SpPage>;

  const view = wq.data;
  const choice = (w: Warning) => local[w.id] ?? w.decision?.option_key ?? w.default_option ?? undefined;
  const decided = items.filter((w) => choice(w)).length;
  const shown = items.filter((w) => filter === 'all' || GROUP[w.kind] === filter);

  const pick = (w: Warning) => setSp((prev) => { const n = new URLSearchParams(prev); n.set('w', w.id); return n; }, { replace: true });
  const decide = async (w: Warning, key: string) => {
    if (STORED(key)) setLocal((m) => ({ ...m, [w.id]: key }));
    try { await decideWarning(id, w.id, key); } catch (e) { toast(errText(e)); }
  };
  const go = async (w: Warning, key: string, nav_: string | null | undefined) => {
    await decide(w, key);
    if (nav_ === 'SP1C') nav(`/spec/${id}/find?preset=warning:${w.id}`);
    else if (nav_ === 'SP4') nav(`/spec/${id}/export?link=${w.link_id ?? ''}&mode=replace`);
    else if (nav_ === 'SP1R') nav(`/spec/${id}/requirements`);
  };

  const apply = async () => {
    setApplying(true);
    try {
      // 기본 선택도 결정으로 저장한 뒤 한 번에 반영
      for (const w of items) {
        const k = choice(w);
        if (k && !w.decision && STORED(k)) await decideWarning(id, w.id, k);
      }
      const r = await applyWarnings(id);
      cache.put(r);
      void cache.refreshWarnings(id);
      if (r.active_job && r.ui_status === 'run') nav(`/spec/${id}/generating?job=${r.active_job.id}`);
      else nav(`/spec/${id}`);
    } catch (e) { toast(errText(e)); } finally { setApplying(false); }
  };

  const fc = view.counts;
  const filters: Array<[Filter, string, number]> = [['all', '전체', fc.all ?? 0], ['discontinued', '단종', fc.discontinued ?? 0], ['mismatch', '값 불일치', fc.mismatch ?? 0], ['unmet', '요구 미충족', fc.unmet ?? 0]];

  return (
    <div className="sp-wpage">
      <SpPage width={700}
        dock={
          <Dock title="Spec 시트" meta="3 / 3 · 경고 확인 중"
            right={
              <button type="button" className="sp-pillbtn" onClick={() => nav(`/spec/${id}/edit`)}>
                <PathIcon d="M4 20h4L19 9l-4-4L4 16v4z" size={12} strokeWidth={2.2} />시트 직접 편집
              </button>
            }
            row={<PromptInput label="수정 요청" placeholder="수정 요청 (예: QM55R 열 이름을 '기존 장비'로)" onSend={revise.send} busy={revise.busy} />}
          />
        }>
        {picker.input}
        {(revise.userText ?? view.user_text) && <UserBubble>{revise.userText ?? view.user_text}</UserBubble>}
        <Agent text={revise.busy ? '요청을 반영하고 있어요…' : (revise.reply && !items.length ? revise.reply : view.agent_text)}>
          {items.length > 0 ? (
            <WarnTable s={s} items={items} sel={sel} onPick={pick} footer={view.footer} />
          ) : <div className="sp-note">확인할 경고가 없어요.</div>}
        </Agent>
      </SpPage>

      <aside className="sp-wpanel" aria-label="확인이 필요한 곳">
        <div className="sp-wpanel__head">
          <div className="sp-wpanel__top">
            <div className="sp-wpanel__title">
              <PathIcon d={TRI} size={17} strokeWidth={2.2} color="var(--wm-brand)" />
              <span>확인이 필요한 곳</span>
              <span className="sp-wpanel__count">{items.length}</span>
            </div>
            <button type="button" className="sp-icbtn sp-icbtn--close" aria-label="닫기" onClick={() => nav(`/spec/${id}`)}>
              <PathIcon d="M6 6l12 12M18 6L6 18" size={16} strokeWidth={2.2} />
            </button>
          </div>
          <div className="sp-chiprow">
            {filters.map(([k, label, n]) => (
              <button key={k} type="button" className="sp-chip sp-chip--h28" aria-pressed={filter === k} onClick={() => setFilter(k)}>{label} {n}</button>
            ))}
          </div>
        </div>
        <div className="sp-wpanel__list" ref={listRef}>
          {shown.map((w) => {
            const g = GROUP[w.kind];
            const c = choice(w);
            const radios = (w.options ?? []).filter((o) => o.kind === 'radio');
            const chips = (w.options ?? []).filter((o) => o.kind === 'chip');
            const buttons = (w.options ?? []).filter((o) => o.kind === 'button');
            const isSel = sel?.id === w.id;
            return (
              <div key={w.id} className={cx('sp-wc', isSel && 'sp-wc--sel')} data-testid="sp-warning" data-kind={w.kind} data-selected={isSel ? 'true' : undefined}
                onClick={() => pick(w)}>
                <div className="sp-wc__top">
                  <span className="sp-wc__n">{w.n}</span>
                  <span className={cx('sp-wc__tag', `sp-wc__tag--${g}`)}>{w.tag}</span>
                  <span className="sp-wc__title">{w.title}</span>
                </div>
                <div className="sp-wc__body">{w.body}</div>
                {w.replacement && (
                  <div className="sp-wc__repl">
                    <PathIcon d="M3 5h18v11H3z M12 16v3M8 19h8" size={22} strokeWidth={1.7} />
                    <div className="sp-wc__repltext">
                      <span className="sp-wc__repllabel">현행 대체 모델</span>
                      <span><b>{w.replacement.label}</b> · {w.replacement.relation_text}</span>
                    </div>
                    {buttons.filter((o) => o.key === 'find_other').map((o) => (
                      <button key={o.key} type="button" className="sp-link" onClick={(e) => { e.stopPropagation(); void go(w, o.key, o.navigates_to); }}>{o.label}</button>
                    ))}
                  </div>
                )}
                {radios.length > 0 && (
                  <div className="sp-wc__radios" role="radiogroup" aria-label={`${w.n}번 처리`}>
                    {radios.map((o) => (
                      <button key={o.key} type="button" role="radio" aria-checked={c === o.key} className="sp-wc__radio"
                        onClick={(e) => { e.stopPropagation(); void decide(w, o.key); }}>
                        <span className="sp-wc__dot" />{o.label}
                      </button>
                    ))}
                  </div>
                )}
                {(chips.length > 0 || buttons.some((o) => o.key !== 'find_other')) && (
                  <div className="sp-wc__ctl">
                    {chips.map((o) => (
                      <button key={o.key} type="button" className="sp-chip sp-chip--h28" aria-pressed={c === o.key}
                        onClick={(e) => { e.stopPropagation(); void decide(w, o.key); }}>{o.label}</button>
                    ))}
                    {chips.length > 0 && w.kind === 'value_mismatch_source' && (
                      <button type="button" className="sp-link sp-wc__src" onClick={(e) => { e.stopPropagation(); setSrc(w); }}>출처</button>
                    )}
                    {buttons.filter((o) => o.key !== 'find_other').map((o) => (
                      <button key={o.key} type="button" aria-pressed={o.navigates_to ? undefined : c === o.key}
                        className={cx('sp-wc__btn', o.key === 'reflect' && 'sp-wc__btn--brand', o.key === 'view' && 'sp-wc__btn--bold')}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (o.key === 'upload_datasheet') { dsTarget.current = w; picker.open(); return; }
                          if (o.navigates_to) void go(w, o.key, o.navigates_to); else void decide(w, o.key);
                        }}
                        disabled={o.key === 'upload_datasheet' && !!dsJob}>
                        {o.key === 'reflect' && <PathIcon d="M5 12h14M13 6l6 6-6 6" size={12} strokeWidth={2.2} />}
                        {o.key === 'view' && <PathIcon d="M4 4h16v16H4z M4 10h16M10 4v16" size={12} />}
                        {o.key === 'upload_datasheet' && dsJob ? '데이터시트를 읽고 있어요' : o.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <div className="sp-wpanel__foot">
          <span className="sp-wpanel__dec" data-testid="sp-decided">결정 <b className="sp-numf">{decided}</b> / {items.length}</span>
          <div className="sp-chiprow">
            <button type="button" className="sp-wbtn" onClick={() => nav(`/spec/${id}`)}>나중에</button>
            <button type="button" className="sp-wbtn sp-wbtn--primary" onClick={() => void apply()} disabled={applying || !items.length}>
              <PathIcon d="M5 12l5 5L20 7" size={14} strokeWidth={2.4} />선택한 대로 반영
            </button>
          </div>
        </div>
      </aside>
      <SourcesModal sheetId={id} rowId={src?.row_id} productId={src?.product_id} title={src ? `${src.title} · 출처` : ''} onClose={() => setSrc(null)} />
    </div>
  );
}
