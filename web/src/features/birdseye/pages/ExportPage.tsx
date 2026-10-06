/** BE6 — 내보내기 · 보내기(`/birdseye/:id/export`, `?map=BV-B|ZP`, §4.13): 이미지 · 형식 · 크기 · 수량표 · 제안서 매핑 · 시나리오 · Spec · 보기 링크 · ZIP. */
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { api, unwrap } from '@/api/client';
import { useJob } from '@/api/jobs';
import { Modal, Toggle, toast } from '@/ui';
import { be, errText, qk, useBe } from '../api';
import { Agent, BePage, Dock, FieldLabel, Loading, MainButton, Pill, SubButton, useBeShell } from '../ui';

const W6 = '조감도 결과를 내려받거나 다른 작업으로 보낼 수 있어요. 이미지와 함께 배치안의 제품 수량표가 넘어가고, 수량은 배치안 기준이라 견적 전에 한 번 확인해 주세요.';
type Fmt = 'png' | 'jpg' | 'pdf';
type ProposalRow = { id: string; title: string; type_label?: string | null; meta?: string; project_id?: string | null };

export default function ExportPage() {
  const { id = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const bq = useBe(id);
  const oq = useQuery({ queryKey: qk.options(id), queryFn: () => be.exportOptions(id) });
  const qq = useQuery({ queryKey: qk.quantities(id), queryFn: () => be.quantities(id) });
  const props = useQuery({
    queryKey: ['proposal', 'list', 'be6'], retry: 0,
    queryFn: async () => unwrap(await api.proposal.GET('/v1/proposals', { params: { query: { tab: 'all', limit: 20 } as never } })).items as unknown as ProposalRow[],
  });
  const [sel, setSel] = useState<Record<string, boolean> | null>(null);
  const [fmt, setFmt] = useState<Fmt>('png');
  const [size, setSize] = useState<'original' | 'fhd'>('original');
  const [furn, setFurn] = useState(true);
  const [filename, setFilename] = useState<string | null>(null);
  const [maps, setMaps] = useState<Record<string, boolean> | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  const [pick, setPick] = useState(false);
  const [job, setJob] = useState<{ job: string; xid: string } | null>(null);
  const [sending, setSending] = useState(false);
  useBeShell(bq.data, 5, {}, true);
  useJob(job?.job, {
    onDone: async (j) => {
      const x = job;
      setJob(null);
      if (!x) return;
      if (j.status !== 'succeeded') { toast('내보내기를 만들지 못했어요'); return; }
      const rec = await be.exportRecord(x.xid);
      if (rec.download_url) window.location.assign(rec.download_url);
    },
  });
  const o = oq.data;
  useEffect(() => {
    if (!o) return;
    if (!sel) setSel(Object.fromEntries(o.images.map((i) => [`${i.kind}:${i.ref}`, i.selected])));
    if (filename === null) setFilename(o.filename_default);
    if (!maps) {
      const m = sp.get('map');
      setMaps(Object.fromEntries(o.mapping.map((r) => [r.code, !m || r.code === m || (m === 'ZP' && r.code.startsWith('ZP'))])));
    }
  }, [o]); // eslint-disable-line react-hooks/exhaustive-deps
  const proposals = props.data ?? [];
  // 기본 보낼 곳: 제안서 섹션 「조감도 새로 만들기」로 왔으면(origin.return_to) 그 제안서 → 같은 프로젝트의 최근 제안서 → 가장 최근(통합)
  useEffect(() => {
    if (target || !proposals.length) return;
    const back = (bq.data?.origin as { return_to?: string | null } | null | undefined)?.return_to ?? '';
    const fromBack = back.match(/\/proposal\/(pr_[0-9A-Z]+)/)?.[1];
    const prj = bq.data?.project_id ?? null;
    const pick0 = proposals.find((p) => p.id === fromBack) ?? (prj ? proposals.find((p) => p.project_id === prj) : undefined) ?? proposals[0];
    setTarget(pick0.id);
  }, [proposals.length, bq.data?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const chosen = useMemo(() => (o?.images ?? []).filter((i) => sel?.[`${i.kind}:${i.ref}`]), [o, sel]);

  if (bq.isLoading || oq.isLoading || !o) return <Loading />;
  const b = bq.data!;
  const q = qq.data;
  const prop = proposals.find((p) => p.id === target);
  const zipLine = `· 이미지 ${chosen.length}장 · 수량표 1개 · ZIP`;

  const download = async () => {
    try {
      const r = await be.createExport(id, { items: chosen.map((i) => ({ kind: i.kind, ref: i.ref ?? null })), format: fmt, size, include_furniture: furn,
        filename: (filename || o.filename_default).trim() });
      setJob({ job: r.job_id, xid: r.export_id });
    } catch (e) { toast(errText(e)); }
  };
  const send = async () => {
    if (!prop) return;
    setSending(true);
    try {
      const keys = o.mapping.filter((m) => maps?.[m.code]).map((m) => m.code);
      const res = unwrap(await api.proposal.POST('/v1/proposals/{proposal_id}/imports', {
        params: { path: { proposal_id: prop.id } },
        body: { section_key: 'birdseye', via: 'handoff', source: { feature: 'birdseye', ref_id: id, version: o.version, title: o.title }, include_keys: keys } as never,
      })) as { toast?: string; route?: string; section_key?: string | null };
      // 넣을 섹션은 제안서가 정한다(퀵윈 · Solution형엔 「조감도」 섹션이 없다) — 응답 section_key 로 연다
      const to = res?.route || (res?.section_key ? `/proposal/${prop.id}/sections/${res.section_key}` : `/proposal/${prop.id}`);
      toast(res?.toast || `${prop.title}에 넣었어요`, { action: { label: '열기', onClick: () => nav(to) } });
    } catch (e) { toast(errText(e)); } finally { setSending(false); }
  };
  const share = async () => {
    try {
      const r = unwrap(await api.workspace.POST('/v1/share-links', { body: { target: id, route: `/birdseye/${id}/result`, title: b.title } as never })) as { url: string };
      const url = new URL(r.url, window.location.origin).toString();
      await navigator.clipboard?.writeText(url).catch(() => undefined);
      toast('링크를 복사했어요');
    } catch (e) { toast(errText(e)); }
  };
  const spec = () => {
    const models = (o.spec_products ?? []).map((p) => p.model_code).filter(Boolean).join(',');
    // Spec 은 `?models=&from=birdseye:{id}` 로 출처를 받는다(라우트 상태는 읽지 않음)
    nav(`/spec/new?${models ? `models=${encodeURIComponent(models)}&` : ''}from=${encodeURIComponent(`birdseye:${id}`)}`, { state: { from: 'birdseye', ref: id, products: o.spec_products, family_ids: o.family_ids } });
  };

  return (
    <BePage testId="be6" dock={(
      <Dock title="내려받기" meta={zipLine.replace(/^· /, '')}
        foot={(
          <>
            <div className="be-filename">
              <label htmlFor="be6-fn" className="wm-sr-only">파일 이름</label>
              <input id="be6-fn" value={filename ?? ''} onChange={(e) => setFilename(e.target.value)} placeholder="파일 이름" data-testid="be6-filename" />
              <span>.zip</span>
            </div>
            <span style={{ flex: 1 }} />
            <SubButton to={`/birdseye/${id}/result`}>이전</SubButton>
            <MainButton onClick={() => void download()} busy={!!job} testId="be6-zip" arrow={false}>ZIP 내려받기</MainButton>
          </>
        )} />
    )}>
      <Agent text={W6}>
        <section className="be-sec" aria-label="이미지">
          <div className="be-sec__head"><b>이미지</b><span data-testid="be6-count">{chosen.length}</span><span>/ {o.images.length} 선택</span></div>
          <div className="be-imgopts" data-testid="be6-images">
            {o.images.map((i) => {
              const key = `${i.kind}:${i.ref}`;
              const on = !!sel?.[key];
              return (
                <label key={key} className={on ? 'be-imgopt be-imgopt--on' : 'be-imgopt'}>
                  <input type="checkbox" checked={on} onChange={() => setSel({ ...(sel ?? {}), [key]: !on })} />
                  {i.thumb_url ? <img src={i.thumb_url} alt="" /> : <span className="ph" />}
                  <span><b>{i.name}</b><small>{i.sub}</small></span>
                </label>
              );
            })}
          </div>
          <div className="be-row">
            <FieldLabel>형식</FieldLabel>
            {(['png', 'jpg', 'pdf'] as const).map((f) => <Pill key={f} on={fmt === f} onClick={() => setFmt(f)}>{f.toUpperCase()}</Pill>)}
            <span className="be-sep" />
            <FieldLabel>크기</FieldLabel>
            <Pill on={size === 'original'} onClick={() => setSize('original')}>원본</Pill>
            <Pill on={size === 'fhd'} onClick={() => setSize('fhd')}>FHD</Pill>
          </div>
        </section>
        <section className="be-sec be-card" aria-label="제품 수량표">
          <div className="be-sec__head"><b>제품 수량표</b><span>배치안 기준 · Excel</span></div>
          <table className="be-qty" data-testid="be6-qty">
            <thead><tr><th>제품</th><th>위치</th><th style={{ textAlign: 'right' }}>수량</th></tr></thead>
            <tbody>
              {(q?.rows ?? []).map((r, i) => (
                <tr key={i}><td>{r.name}{r.confirm && <span className="be-small" style={{ color: 'var(--wm-warn)' }}> · 확인 필요</span>}</td><td>{r.at}</td><td className="n">{r.qty}</td></tr>
              ))}
              {q?.furniture_row && <tr className="muted"><td>{q.furniture_row.label}</td><td>{q.furniture_row.at}</td><td className="n">{q.furniture_row.qty}</td></tr>}
            </tbody>
          </table>
          {!!q?.memos?.length && <div className="be-note">메모 · {q.memos.join(' / ')}</div>}
          <div className="be-row">
            <Toggle checked={furn} onChange={setFurn}>가구도 함께</Toggle>
            <Toggle checked onChange={() => undefined}>단가 · 견적은 넣지 않아요</Toggle>
          </div>
        </section>
        <section className="be-sec be-card" aria-label="B2B 제안서로 보내기" data-testid="be6-proposal">
          <div className="be-sec__head" style={{ justifyContent: 'space-between' }}>
            <span><b>B2B 제안서로 보내기</b> <span>{prop ? `${prop.title}${prop.type_label ? ` · ${prop.type_label}` : ''}` : '진행 중인 제안서가 없어요'}</span></span>
            {proposals.length > 0 && <button type="button" className="be-link" onClick={() => setPick(true)}>바꾸기</button>}
          </div>
          <div className="be-map" data-testid="be6-map">
            {o.mapping.map((m) => (
              <div key={m.code} className="be-map__row">
                <label>
                  <input type="checkbox" checked={!!maps?.[m.code]} onChange={() => setMaps({ ...(maps ?? {}), [m.code]: !maps?.[m.code] })} />
                  <span>{m.from}</span><span className="to">→ {m.to}</span>
                </label>
                <span className="be-code">{m.code}</span>
              </div>
            ))}
          </div>
          <div className="be-row" style={{ justifyContent: 'flex-end' }}>
            <Link className="be-link" to={`/proposal/new?link=${id}`}>새 제안서로 시작</Link>
            <button type="button" className="be-btn be-btn--sm" onClick={() => void send()} disabled={!prop || sending || !Object.values(maps ?? {}).some(Boolean)}
              data-testid="be6-send">제안서에 넣기</button>
          </div>
        </section>
        <div className="be-sendcard">
          <div><b>공간 시나리오로 이어 만들기</b><span>존 {o.zones_count}곳을 공간으로 가져와 장면을 만들어요</span></div>
          <Link className="be-btn be-btn--sm" to={`/scenario/new/birdseye?birdseye=${id}`} data-testid="be6-scenario">시작</Link>
        </div>
        <div className="be-sendcard">
          <div><b>Spec 시트 만들기</b><span>제품 {o.products_count}종으로 스펙 비교표를 만들어요</span></div>
          <button type="button" className="be-btn be-btn--sm" onClick={spec} data-testid="be6-spec">시작</button>
        </div>
        <div className="be-sendcard">
          <div><b>보기 전용 링크</b><span>팀원이 조감도와 수량표를 볼 수 있어요</span></div>
          <button type="button" className="be-btn be-btn--sm" onClick={() => void share()} data-testid="be6-share">링크 복사</button>
        </div>
        <span className="be-note" data-testid="be6-zipline">내려받기 {zipLine}</span>
      </Agent>
      <Modal open={pick} onClose={() => setPick(false)} title="보낼 제안서" width={520}>
        <div className="be-cutrows">
          {proposals.map((p) => (
            <button key={p.id} type="button" className={p.id === target ? 'be-cutrow be-cutrow--cmp' : 'be-cutrow'} onClick={() => { setTarget(p.id); setPick(false); }}>
              <span className="grow" style={{ textAlign: 'left' }}><b>{p.title}</b><br /><span className="be-small be-muted">{p.meta || p.type_label}</span></span>
            </button>
          ))}
        </div>
      </Modal>
    </BePage>
  );
}
