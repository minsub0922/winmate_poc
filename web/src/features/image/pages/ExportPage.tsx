/**
 * IMG4 · 내보내기 · 제안서에 넣기(§4.11) — 들어오면 현재 버전을 내 이미지에 저장한다.
 * 파일로 받기: PNG · JPG 는 바로(200), 「수정 전 원본도 함께」 · PDF · PPTX 는 export job(202) → 끝나면 내려받기.
 * 제안서에 넣기: 제안서 계약(웹에서만)으로 목록 · 이미지 자리 · 가져오기를 부른다(계약이 없으면 빈 상태).
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Button, cx, ErrorState, Icon, Img, Spinner, toast } from '@/ui';
import { createShareLink, errMessage, img, proposal, type ExportOut, type Version } from '../api';
import { AskInput, Ico, Loading, PATH, Pill, Screen, Seg, useImgShell, WSay } from '../components';
import { useImage, useInvalidate, useWork } from '../hooks';
import { josa, route, sizeFor, sizeLabel, STYLE_LABEL } from '../lib';

type Fmt = 'png' | 'jpg' | 'pdf' | 'pptx';
const FORMATS: Array<{ key: Fmt; name: string; desc: string }> = [
  { key: 'png', name: 'PNG', desc: '원본 화질' }, { key: 'jpg', name: 'JPG', desc: '용량 작게' }, { key: 'pdf', name: 'PDF', desc: '인쇄 · 검토용' }, { key: 'pptx', name: 'PPTX', desc: '슬라이드 1장' },
];
const extOf = (f: Fmt) => f;
const swapExt = (name: string, f: Fmt) => (name.replace(/\.[A-Za-z0-9]{2,5}$/, '') || 'image') + `.${extOf(f)}`;

function relSaved(iso?: string) {
  if (!iso) return '저장됨';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return '방금 저장';
  if (s < 3600) return `${Math.floor(s / 60)}분 전 저장`;
  return `${Math.floor(s / 3600)}시간 전 저장`;
}

export default function ExportPage() {
  const { workId = '', imageId = '' } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const inv = useInvalidate();
  const wq = useWork(workId);
  const iq = useImage(imageId);
  const image = iq.data;
  const versionId = sp.get('version') ?? image?.current_version_id ?? null;
  const ver: Version | null = useMemo(() => image?.versions?.find((v) => v.id === versionId) ?? image?.current ?? null, [image, versionId]);
  const [saved, setSaved] = useState<boolean | null>(null);
  const [fmt, setFmt] = useState<Fmt>('png');
  const [res, setRes] = useState<'fhd' | 'uhd'>('uhd');
  const [aiLabel, setAiLabel] = useState(true);
  const [withOrig, setWithOrig] = useState(false);
  const [fname, setFname] = useState('');
  const [caption, setCaption] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [exp, setExp] = useState<ExportOut | null>(null);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [propId, setPropId] = useState<string | null>(null);
  const [sheetId, setSheetId] = useState<string | null>(null);
  const [mode, setMode] = useState<'replace_slot' | 'new_sheet'>('replace_slot');
  const [also, setAlso] = useState<string[] | null>(() => { const a = sp.get('also'); return a ? a.split(',').filter(Boolean) : null; });
  const savedOnce = useRef(false);

  // 들어오면 내 이미지에 저장(§4.11)
  useEffect(() => {
    if (!imageId || savedOnce.current) return;
    savedOnce.current = true;
    img.save(imageId).then((r) => { setSaved(r.saved); void inv.gallery(); }).catch(() => setSaved(false));
  }, [imageId, inv]);
  // 기본 파일명(서버 규칙)
  useEffect(() => {
    if (!image || fname) return;
    img.filename(image.id, { lang: 'ko', ext: 'png', version_id: versionId ?? undefined }).then((r) => setFname(r.filename)).catch(() => setFname(`${image.label.replace(/\s+/g, '')}.png`));
  }, [image, versionId, fname]);
  // export job 이 끝날 때까지
  useEffect(() => {
    if (!exp || exp.status === 'done' || exp.status === 'failed') return;
    const t = window.setInterval(async () => {
      try {
        const cur = await img.exportStatus(exp.export_id);
        setExp(cur);
        if (cur.status === 'done' && cur.download_url) { window.location.assign(cur.download_url); setMsg({ text: `${cur.filename} 파일을 만들었어요`, ok: true }); void inv.work(workId); }
        if (cur.status === 'failed') setMsg({ text: (cur.error as { message?: string } | null)?.message ?? '파일을 만들지 못했어요', ok: false });
      } catch { /* 다음 차례에 */ }
    }, 1_200);
    return () => window.clearInterval(t);
  }, [exp, inv, workId]);

  const props = useQuery({ queryKey: ['image', 'proposals'], queryFn: proposal.list, staleTime: 30_000, retry: 0 });
  const plist = props.data?.items ?? [];
  useEffect(() => { if (!propId && plist.length) setPropId((plist.find((p) => p.project_id && p.project_id === wq.data?.project_id) ?? plist[0]).id); }, [plist, propId, wq.data?.project_id]);
  const slots = useQuery({ queryKey: ['image', 'slots', propId, versionId], queryFn: () => proposal.slots(propId!, versionId!), enabled: !!propId && !!versionId, retry: 0 });
  const sheets = slots.data?.sheets ?? [];
  useEffect(() => { if (sheets.length && !sheets.some((s) => s.sheet_id === sheetId)) setSheetId((sheets.find((s) => s.recommended) ?? sheets[0]).sheet_id); }, [sheets, sheetId]);
  const prop = plist.find((p) => p.id === propId) ?? null;
  const sheet = sheets.find((s) => s.sheet_id === sheetId) ?? null;
  const siblings = useQuery({ queryKey: ['image', 'siblings', workId], queryFn: () => img.images({ work_id: workId, limit: 20 }), enabled: also !== null });

  const download = async () => {
    if (!image) return;
    setBusy('dl'); setMsg(null); setExp(null);
    try {
      const out = await img.exportImage(image.id, { version_id: versionId, format: fmt, resolution: res, ai_label: aiLabel, include_original: withOrig, filename: fname || null, caption });
      if (out.status === 'done' && out.download_url) { window.location.assign(out.download_url); setMsg({ text: `${out.filename} 파일을 내려받았어요`, ok: true }); void inv.work(workId); }
      else { setExp(out); setMsg({ text: '파일을 만드는 중이에요', ok: true }); }
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const doCaption = async () => {
    if (!image) return;
    setBusy('cap');
    try { const r = await img.caption(image.id); setCaption(r.caption); } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const doEnglish = async () => {
    if (!image) return;
    setBusy('en');
    try { const r = await img.filename(image.id, { lang: 'en', ext: fmt, version_id: versionId ?? undefined }); setFname(r.filename); } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const ask = async (text: string) => {
    if (!image) return;
    setBusy('ask'); setMsg(null);
    try {
      const r = await img.interpret(image.id, { text, screen: 'export' });
      const o = r.options as { caption?: boolean; english_filename?: boolean; format?: Fmt; include_original?: boolean; ai_label?: boolean; resolution?: 'fhd' | 'uhd' };
      if (r.action !== 'export_options') { setMsg({ text: r.question ?? '내보내기 옵션으로 이해하지 못했어요', ok: false }); return; }
      if (o.format && FORMATS.some((f) => f.key === o.format)) { setFmt(o.format); setFname((n) => swapExt(n, o.format!)); }
      if (typeof o.include_original === 'boolean') setWithOrig(o.include_original);
      if (typeof o.ai_label === 'boolean') setAiLabel(o.ai_label);
      if (o.resolution) setRes(o.resolution);
      if (o.english_filename) await doEnglish();
      if (o.caption) await doCaption();
      setMsg({ text: '요청대로 내보내기 옵션을 바꿨어요', ok: true });
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); } finally { setBusy(null); }
  };
  const insert = async () => {
    if (!image || !versionId || !prop) return;
    setBusy('insert'); setMsg(null);
    try {
      const ids = [image.id, ...(also ?? [])];
      for (const id of ids) {
        const vid = id === image.id ? versionId
          : (siblings.data?.items.find((t) => t.id === id)?.current_version_id ?? (await img.image(id).catch(() => null))?.current_version_id ?? null);
        if (!vid) continue;
        await proposal.importImage(prop.id, { source: { service: 'image', version_id: vid, image_id: id }, target: { sheet_id: sheet?.sheet_id ?? null, mode }, caption });
      }
      const where = `${prop.short_title ?? prop.title}${sheet ? ` › ${sheet.name}` : ''}`;
      toast(`${where}에 넣었어요`, { action: { label: '열기', onClick: () => nav(`/proposal/${prop.id}`) } });
      void inv.work(workId); void inv.gallery();
    } catch { setMsg({ text: '제안서에 넣지 못했어요 · 다시 시도', ok: false }); } finally { setBusy(null); }
  };
  const toScenario = async () => {
    if (!image || !versionId) return;
    const reqId = wq.data?.origin?.request_id;
    try {
      if (reqId && wq.data?.origin?.service === 'scenario') await img.fulfillRequest(reqId, versionId);
      nav(`/scenario?image_version=${encodeURIComponent(versionId)}${reqId ? `&request=${encodeURIComponent(reqId)}` : ''}`);
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); }
  };
  const share = async () => {
    if (!image) return;
    try {
      const url = await createShareLink(`img:image:${image.id}`, route.exportTo(workId, image.id, versionId), ver?.title ?? image.title);
      const full = `${window.location.origin}${url}`;
      await navigator.clipboard?.writeText(full).catch(() => undefined);
      setMsg({ text: `공유 링크를 복사했어요 · ${full}`, ok: true });
    } catch (e) { setMsg({ text: errMessage(e), ok: false }); }
  };

  useImgShell({ title: wq.data?.title ?? '내보내기', step: 3, complete: true });
  if (iq.isLoading) return <Loading />;
  if (!image || !ver) return <div className="img-center"><ErrorState message="시안을 불러오지 못했어요" onRetry={() => iq.refetch()} /></div>;
  const [fw, fh] = sizeFor(image.aspect, 'fhd');
  const [uw, uh] = sizeFor(image.aspect, 'uhd');
  const edited = ver.n > 1;
  const w1 = `${image.label}${edited ? (ver.op === 'adjust' ? ' 보정본' : ' 수정본') : ''}`;
  const wText = `${w1}${josa(w1, '을', '를')} 내보냅니다. 파일로 받거나, 진행 중인 제안서의 이미지 자리에 바로 넣을 수 있어요. 넣을 시트는 장면에 맞춰 추천해 두었습니다.`;
  const fmtName = FORMATS.find((f) => f.key === fmt)!.name;
  const exporting = !!exp && exp.status !== 'done' && exp.status !== 'failed';
  return (
    <Screen testid="img4" composer={
      <div className="wm-composer-wrap">
        <div className="wm-composer">
          <div className="wm-composer__head">
            <span data-testid="img4-head">내보내기{prop && <small> · {prop.short_title ?? prop.title}{sheet ? ` › ${sheet.name}` : ''}</small>}</span>
            <span className="img-quick">
              <Pill on={also !== null} onClick={() => setAlso(also === null ? [] : null)}>다른 시안도 함께 넣기</Pill>
              <Pill disabled={busy === 'cap'} onClick={() => void doCaption()}>캡션 자동 작성</Pill>
              <Pill disabled={busy === 'en'} onClick={() => void doEnglish()}>영문 파일명</Pill>
            </span>
          </div>
          {also !== null && (
            <div style={{ padding: '10px 18px 0' }} className="img-row" data-testid="img4-also">
              <span className="img-label">함께 넣을 시안</span>
              {(siblings.data?.items ?? []).filter((t) => t.id !== image.id && t.status === 'done').map((t) => (
                <Pill key={t.id} h={28} on={also.includes(t.id)} onClick={() => setAlso(also.includes(t.id) ? also.filter((x) => x !== t.id) : [...also, t.id])}>{t.label}</Pill>
              ))}
            </div>
          )}
          {caption !== null && (
            <div style={{ padding: '10px 18px 0' }} className="img-row">
              <label htmlFor="img-cap" className="img-label" style={{ flexShrink: 0 }}>캡션</label>
              <input id="img-cap" className="img-fname" value={caption} onChange={(e) => setCaption(e.target.value)} />
            </div>
          )}
          {msg && <div className={cx('img-askline', !msg.ok && 'img-err')} role="status" data-testid="img4-msg">{exporting ? <Spinner /> : <Icon name={msg.ok ? 'check' : 'info'} size={13} />}{msg.text}</div>}
          <div className="wm-composer__foot">
            <AskInput label="내보내기 요청" placeholder="요청 (예: 넣을 때 아래에 캡션도 달아줘)" busy={busy === 'ask'} onSend={ask} testid="img4-ask" />
            <Button h={44} onClick={() => nav(route.result(workId, image.id))}>결과로 돌아가기</Button>
            <Button h={44} variant="primary" disabled={!prop || busy === 'insert'} loading={busy === 'insert'} disabledReason="넣을 제안서가 없어요"
              onClick={() => void insert()} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>제안서에 넣기</Button>
          </div>
        </div>
      </div>
    }>
      <WSay text={wText}>
        <div className="img-card">
          <div className="img-exp__head">
            <span className="img-exp__thumb"><Img src={ver.thumb_url} alt={`${ver.title}`} /></span>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}>
              <div className="wm-ellipsis" style={{ fontSize: 13.5, fontWeight: 600 }} data-testid="img4-title">{ver.title}</div>
              <div className="img-hint img-hint--sm" style={{ whiteSpace: 'nowrap' }}>
                <span className="wm-num" style={{ fontWeight: 600 }}>{image.aspect} · {res === 'uhd' ? sizeLabel(uw, uh) : sizeLabel(fw, fh)}</span> · {STYLE_LABEL[image.style] ?? '실사 렌더'} · {saved ? '방금 저장' : relSaved(ver.created_at)}
              </div>
            </div>
            <Link to={route.result(workId, image.id)} className="img-btn30">다른 시안 고르기</Link>
            <Link to={route.variants(workId, image.id)} className="img-btn30">비율 · 해상도 바꾸기</Link>
          </div>
          <div className="img-exp__body">
            <div className="img-exp__file">
              <div className="img-exp__h"><Icon name="download" size={15} color="var(--wm-brand)" />파일로 받기</div>
              <div role="radiogroup" aria-label="파일 형식" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 8 }}>
                {FORMATS.map((f) => (
                  <button key={f.key} type="button" role="radio" aria-checked={fmt === f.key} className="img-radio img-fmt" onClick={() => { setFmt(f.key); setFname((n) => swapExt(n, f.key)); }}>
                    <span className="img-radio__dot" />
                    <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
                      <span className="img-fmt__name">{f.name}</span><span className="img-fmt__desc">{f.desc}</span>
                    </span>
                  </button>
                ))}
              </div>
              <div className="img-row" style={{ minHeight: 30 }}>
                <span className="img-label" style={{ width: 36 }}>해상도</span>
                <Seg ariaLabel="해상도" size="sm" value={res} onChange={setRes} items={[
                  { value: 'fhd', label: <span className="wm-num">{sizeLabel(fw, fh)}</span> }, { value: 'uhd', label: <span className="wm-num">{sizeLabel(uw, uh)}</span> },
                ]} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label className="img-check"><input type="checkbox" checked={aiLabel} onChange={(e) => setAiLabel(e.target.checked)} />AI 생성 이미지 표기 넣기</label>
                <label className="img-check"><input type="checkbox" checked={withOrig} onChange={(e) => setWithOrig(e.target.checked)} />수정 전 원본도 함께</label>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label htmlFor="img-fname" className="img-label">파일명</label>
                <input id="img-fname" className="img-fname" value={fname} onChange={(e) => setFname(e.target.value)} data-testid="img4-fname" />
              </div>
              <button type="button" className="img-dlbtn" disabled={busy === 'dl' || exporting} onClick={() => void download()}>
                {busy === 'dl' || exporting ? <Spinner /> : <Ico d={PATH.download} size={14} />}{fmtName} 다운로드
              </button>
            </div>
            <div className="img-exp__prop">
              <div className="img-row" style={{ justifyContent: 'space-between' }}>
                <div className="img-exp__h"><Ico d={PATH.present} size={15} color="var(--wm-brand)" />제안서에 넣기</div>
                <Link to={`/proposal/new?image_version=${encodeURIComponent(versionId ?? '')}`} className="img-row" style={{ gap: 4, fontSize: 12, fontWeight: 600 }}>
                  <Icon name="plus" size={12} strokeWidth={2.4} />새 제안서로 시작
                </Link>
              </div>
              {props.isLoading ? <Spinner /> : props.isError ? (
                <div className="img-empty-prop" role="alert">제안서 목록을 불러오지 못했어요<button type="button" className="img-mini" onClick={() => props.refetch()}>다시 시도</button></div>
              ) : plist.length === 0 ? (
                <div className="img-empty-prop" data-testid="img4-noprop">
                  <span>진행 중인 제안서가 없어요</span>
                  <Link to={`/proposal/new?image_version=${encodeURIComponent(versionId ?? '')}`} className="img-btn30">새 제안서로 시작</Link>
                </div>
              ) : (
                <>
                  <div role="radiogroup" aria-label="넣을 제안서" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {plist.map((p) => (
                      <button key={p.id} type="button" role="radio" aria-checked={p.id === propId} className="img-radio img-prop" onClick={() => setPropId(p.id)}>
                        <span className="img-radio__dot" /><span className="img-prop__name">{p.title}</span><span style={{ flex: 1 }} />
                        {p.meta && <span className="img-hint" style={{ fontSize: 11.5, whiteSpace: 'nowrap' }}>{p.meta}</span>}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div className="img-label">넣을 시트 <span style={{ color: 'var(--wm-text-subtle)' }}>· 이미지를 받는 시트만 보여요</span></div>
                    {slots.isLoading ? <Spinner /> : sheets.length === 0 ? <span className="img-hint img-hint--sm">이미지를 받는 시트가 없어요 · 「새 시트로 추가」로 넣을 수 있어요</span> : (
                      <div className="img-row" style={{ alignItems: 'flex-start', gap: 12 }}>
                        <div role="radiogroup" aria-label="넣을 시트" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {sheets.map((s) => (
                            <button key={s.sheet_id} type="button" role="radio" aria-checked={s.sheet_id === sheetId} className="img-radio img-sheet" onClick={() => setSheetId(s.sheet_id)}>
                              <span className="img-radio__dot" />
                              <span style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0, flex: 1 }}>
                                <span className="img-row" style={{ gap: 6 }}><span className="img-sheet__name">{s.name}</span>{s.recommended && <span className="img-rec">추천</span>}</span>
                                {s.section && <span className="img-hint wm-ellipsis" style={{ fontSize: 11.5 }}>{s.section}</span>}
                              </span>
                            </button>
                          ))}
                        </div>
                        {sheet && (
                          <div style={{ width: 186, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <div className="img-sheetpv">
                              {sheet.preview_url ? <Img src={sheet.preview_url} alt={`${sheet.name} 시트 미리보기`} /> : (
                                <>
                                  <i style={{ left: 0, top: 0, width: 186, height: 3, background: 'var(--wm-brand)' }} />
                                  <i style={{ left: 9, top: 11, width: 60, height: 5, background: 'var(--wm-text)' }} />
                                  <i style={{ left: 9, top: 25, width: 60, height: 4, background: 'var(--wm-line)' }} />
                                  <i style={{ left: 9, top: 34, width: 52, height: 4, background: 'var(--wm-line)' }} />
                                  <i style={{ left: 9, top: 62, width: 60, height: 30, background: 'var(--wm-brand-50)' }} />
                                  <span className="img-sheetpv__slot"><Img src={ver.thumb_url} alt="시트 미리보기 속 이미지 자리" /></span>
                                </>
                              )}
                            </div>
                            <span style={{ fontSize: 12, fontWeight: 600 }}>{sheet.name}</span>
                            <span className="img-hint" style={{ fontSize: 11.5 }}>이미지 자리 {sheet.slots ?? 1}곳 · 교체 미리보기</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="img-row" style={{ minHeight: 30 }}>
                    <span className="img-label">넣는 방식</span>
                    <Seg ariaLabel="넣는 방식" size="sm" value={mode} onChange={setMode} items={[{ value: 'replace_slot', label: '이미지 자리 교체' }, { value: 'new_sheet', label: '새 시트로 추가' }]} />
                    <span style={{ flex: 1 }} />
                    <span className="img-hint" style={{ fontSize: 11.5, color: 'var(--wm-text-subtle)' }}>위치 · 크기는 나중에 조정</span>
                  </div>
                </>
              )}
            </div>
          </div>
          <div className="img-exp__foot">
            <span className="img-label" style={{ marginRight: 4 }}>다른 작업에 쓰기</span>
            <button type="button" className="img-pill img-pill--h28" onClick={() => void toScenario()}><Ico d={PATH.play} size={13} />공간 시나리오 장면으로</button>
            <Link to={`/birdseye/new?ref_version=${encodeURIComponent(versionId ?? '')}`} className="img-pill img-pill--h28"><Ico d={PATH.cube} size={13} />조감도 참조로</Link>
            <button type="button" className="img-pill img-pill--h28" onClick={() => void share()}><Ico d={PATH.share} size={13} />팀에 공유</button>
            <span style={{ flex: 1 }} />
            {saved && <span className="img-row img-hint img-hint--sm" style={{ gap: 4 }} data-testid="img4-saved"><Icon name="check" size={12} color="var(--wm-brand)" strokeWidth={2.6} />내 이미지에 저장됨</span>}
            <Link to={route.list()} style={{ fontSize: 12, fontWeight: 600, marginLeft: 4 }}>갤러리 보기</Link>
          </div>
        </div>
      </WSay>
    </Screen>
  );
}
