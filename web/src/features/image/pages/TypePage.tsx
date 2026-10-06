/**
 * IMG1 · 이미지 유형(1/3) — 유형 카드 3 · 장면 설명 · 참조 첨부(§4.2).
 * `?work=` 이면 그 작업을 이어서, `?request=` 이면 요청으로 작업을 만들어(R2) 미리 채운다.
 * 「상세 조건 입력」 = 작업 만들기/고치기 → `:prefill`(동기, 10초) → IMG2.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Button, cx, ErrorState, Icon, Img, useDropTarget } from '@/ui';
import { errMessage, img, type Work } from '../api';
import { Ico, PATH, Screen, useImgShell, WSay } from '../components';
import { useInvalidate, useWork } from '../hooks';
import { route } from '../lib';

type Kind = 'space' | 'background' | 'scenario';
const TYPES: Array<{ kind: Kind; name: string; desc: string; icon: string }> = [
  { kind: 'space', name: '공간', desc: '매장·로비·회의실 등 제품이 설치된 공간 장면', icon: PATH.space },
  { kind: 'background', name: '배경', desc: '표지·섹션 슬라이드용 분위기 배경, 텍스트 영역 확보', icon: PATH.background },
  { kind: 'scenario', name: '시나리오', desc: '사람이 제품을 사용하는 순간을 담은 컷', icon: PATH.scenario },
];

export default function TypePage() {
  const [sp, setSp] = useSearchParams();
  const workId = sp.get('work');
  const requestId = sp.get('request');
  const nav = useNavigate();
  const inv = useInvalidate();
  const work = useWork(workId);
  const [kind, setKind] = useState<Kind>('space');
  const [desc, setDesc] = useState('');
  const [busy, setBusy] = useState<'next' | 'refs' | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const loaded = useRef<string | null>(null);
  const creating = useRef<Promise<string> | null>(null);

  // 요청에서 시작(R2): 작업을 만들고 ?work= 로 바꾼다
  useEffect(() => {
    if (!requestId || workId) return;
    img.startRequest(requestId).then((st) => setSp({ work: st.work_id }, { replace: true })).catch((e) => setErr(errMessage(e)));
  }, [requestId, workId, setSp]);

  useEffect(() => {
    const w = work.data;
    if (!w || loaded.current === w.id) return;
    loaded.current = w.id;
    if (w.kind === 'composite') { nav(route.composite(w.id), { replace: true }); return; }
    setKind(w.kind as Kind);
    setDesc(w.description ?? '');
  }, [work.data, nav]);

  /** 작업이 없으면 만들고, 있으면 바뀐 유형 · 설명을 저장한다 */
  const ensureWork = async (): Promise<string> => {
    const w = work.data;
    if (w) {
      if (w.kind !== kind || (w.description ?? '') !== desc.trim()) {
        const saved = await img.patchWork(w.id, { kind, description: desc.trim() });
        inv.setWork(saved);
      }
      return w.id;
    }
    if (!creating.current) {
      creating.current = img.createWork({ kind, description: desc.trim(), start: 'type' }).then((created: Work) => {
        inv.setWork(created);
        loaded.current = created.id;
        setSp({ work: created.id }, { replace: true });
        return created.id;
      }).finally(() => { creating.current = null; });
    }
    return creating.current;
  };

  const next = async () => {
    if (desc.trim().length < 2 || busy) return;
    setBusy('next'); setErr(null);
    try {
      const id = await ensureWork();
      const pre = await img.prefill(id);
      inv.setWork(pre.work);
      nav(route.conditions(id));
    } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const toRefs = async () => {
    setBusy('refs'); setErr(null);
    try { const id = await ensureWork(); nav(route.references(id)); } catch (e) { setErr(errMessage(e)); } finally { setBusy(null); }
  };
  const addImages = async (refs: string[]) => {
    const id = await ensureWork();
    const added: string[] = [];
    for (const r of refs) {
      try { await img.addReference(id, { source_kind: 'topbar', source_ref: r, via: 'topbar' }); added.push(r); } catch (e) { setErr(errMessage(e)); }
    }
    await inv.work(id);
    return added;
  };

  const refs = work.data?.references ?? [];
  useImgShell({
    title: work.data?.title && work.data.title !== '새 작업' ? work.data.title : '새 작업', step: 1,
    accepts: ['image'], addable: ['image'], added: refs.map((r) => r.source_ref ?? '').filter(Boolean),
    onAdd: async (_type, list) => ({ added: await addImages(list) }),
  });
  const drop = useDropTarget({ accept: ['image'], onDrop: async (p) => { const a = await addImages([p.ref]); return a.length ? true : false; } });

  if (workId && work.isError) return <div className="img-center"><ErrorState message="작업을 불러오지 못했어요" onRetry={() => work.refetch()} /></div>;
  const tooShort = desc.trim().length < 2;
  return (
    <Screen testid="img1" composer={
      <div className="wm-composer-wrap">
        <div className={cx('wm-composer')} style={drop.dragging ? { boxShadow: 'var(--wm-ring-drop)', borderColor: 'var(--wm-brand)' } : undefined} {...drop.props} data-drop-state={drop.state}>
          <div className="wm-composer__head"><span>이미지 유형<small> · 하나 선택 · 1 / 3</small></span></div>
          <div className="wm-composer__body" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div className="img-types" role="radiogroup" aria-label="이미지 유형">
              {TYPES.map((t) => (
                <button key={t.kind} type="button" role="radio" aria-checked={kind === t.kind} className="img-type" onClick={() => setKind(t.kind)}>
                  <span className="img-type__top">
                    <span className="img-type__icon"><Ico d={t.icon} size={18} /></span>
                    <span className="img-type__radio">{kind === t.kind && <Icon name="check" size={11} color="var(--wm-surface)" strokeWidth={3} />}</span>
                  </span>
                  <span className="img-type__name">{t.name}</span>
                  <span className="img-type__desc">{t.desc}</span>
                </button>
              ))}
            </div>
            <label htmlFor="img-desc" className="wm-sr-only">장면 설명</label>
            <textarea id="img-desc" className="img-textarea" maxLength={500} value={desc} onChange={(e) => setDesc(e.target.value)}
              placeholder="예) 카페 카운터 위에 3연 메뉴보드가 걸린 장면, 낮 시간, 손님 2~3명"
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) void next(); }} />
          </div>
          <div className="wm-composer__foot" style={{ justifyContent: 'space-between' }}>
            <div className="img-row" style={{ gap: 6, minWidth: 0 }}>
              <button type="button" className="img-iconbtn" aria-label="참조 이미지 첨부" title="참조 이미지 첨부" onClick={() => void toRefs()} disabled={!!busy}>
                <Icon name="image" size={16} />
              </button>
              {refs.length > 0 ? (
                <>
                  <span className="img-refthumbs">{refs.slice(0, 3).map((r) => <span key={r.id} className="img-refthumb" style={{ width: 40, height: 28 }}><Img src={r.thumb_url} alt={r.label} /></span>)}</span>
                  <span className="img-hint" data-testid="img1-refnote">{work.data?.ref_notice ?? `참조 ${refs.length}장이 들어갔습니다`}</span>
                </>
              ) : <span className="img-hint">{drop.dragging ? '여기에 놓으면 참조 이미지로 들어가요' : "참조 이미지는 상단 '이미지 검색'에서도 가져올 수 있어요"}</span>}
            </div>
            <Button h={44} variant="primary" onClick={() => void next()} disabled={tooShort || !!busy} loading={busy === 'next'}
              disabledReason={tooShort ? '장면을 두 글자 이상 설명해 주세요' : undefined} iconRight={<Icon name="arrowRight" size={16} strokeWidth={2.2} />}>
              상세 조건 입력
            </Button>
          </div>
          {err && <div className="img-askline img-err" role="alert" style={{ paddingBottom: 12 }}>{err}</div>}
        </div>
      </div>
    }>
      <WSay text="어떤 이미지를 만들까요? 제안서에서 쓰일 자리에 따라 유형을 고르고, 원하는 장면을 한두 문장으로 설명해 주세요. 유형에 따라 다음 단계에서 묻는 조건이 달라집니다." />
    </Screen>
  );
}
