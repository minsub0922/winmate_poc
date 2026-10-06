/** BE1 — 공간 입력 1/5(`/birdseye/new` · `/birdseye/:id/space`, §4.2): 공간 유형 칩 6 · 설명 · 면적(평) · 층고(m) · 파일 첨부(R1 분류). */
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { Icon, toast } from '@/ui';
import { be, errText, qk, uploadAll, useBe, useSpace, type Birdseye } from '../api';
import { Agent, BePage, Dock, FieldLabel, Loading, MainButton, Pill, useBeShell } from '../ui';

export const CHIPS: Array<{ value: Birdseye['space_chip']; label: string }> = [
  { value: 'store_lobby', label: '매장 · 로비' }, { value: 'meeting_office', label: '회의실 · 오피스' }, { value: 'classroom', label: '강의실' },
  { value: 'hospital_waiting', label: '병원 대기실' }, { value: 'hotel_room', label: '호텔 객실' }, { value: 'control_room', label: '관제실' },
];
const ACCEPT = '.pdf,.png,.jpg,.jpeg,.heic,.heif,application/pdf,image/png,image/jpeg,image/heic,image/heif';
const OK_TYPES = /\.(pdf|png|jpe?g|heic|heif)$/i;

export default function SpacePage() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const bq = useBe(id);
  const sq = useSpace(id);
  const b = bq.data;
  const [chip, setChip] = useState<Birdseye['space_chip']>('store_lobby');
  const [desc, setDesc] = useState('');
  const [area, setArea] = useState('');
  const [ceil, setCeil] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const loaded = useRef(false);
  const refVersion = sp.get('ref_version');
  const [refThumb, setRefThumb] = useState<string | null>(null);

  useEffect(() => {
    if (b && !loaded.current) {
      loaded.current = true;
      setChip(b.space_chip);
      setDesc(b.description || '');
      setArea(b.area_input_pyeong != null ? String(b.area_input_pyeong) : '');
      setCeil(b.ceiling_input_m != null ? String(b.ceiling_input_m) : '');
    }
  }, [b]);
  useEffect(() => {
    if (!refVersion) return;
    fetch(`/api/image/v1/versions/${refVersion}`, { credentials: 'same-origin' }).then((r) => (r.ok ? r.json() : null))
      .then((v) => setRefThumb(v?.thumb_url ?? v?.url ?? null)).catch(() => undefined);
  }, [refVersion]);

  useBeShell(b, 1);
  if (id && bq.isLoading) return <Loading />;

  const ceilNum = ceil.trim() ? Number(ceil) : null;
  const areaNum = area.trim() ? Number(area) : null;
  const ceilBad = ceilNum !== null && (!Number.isFinite(ceilNum) || ceilNum < 1.8 || ceilNum > 20);
  const areaBad = areaNum !== null && (!Number.isFinite(areaNum) || areaNum <= 0);
  const existing = sq.data?.files ?? [];
  const hasInput = !!desc.trim() || files.length > 0 || existing.length > 0;

  const addFiles = (list: FileList | File[] | null) => {
    if (!list) return;
    const arr = Array.from(list);
    const bad = arr.filter((f) => !OK_TYPES.test(f.name));
    if (bad.length) setErr('PDF · PNG · JPG · HEIC만 올릴 수 있어요');
    else setErr(null);
    setFiles((cur) => [...cur, ...arr.filter((f) => OK_TYPES.test(f.name))]);
  };
  const onDrop = (e: DragEvent) => { e.preventDefault(); setOver(false); addFiles(e.dataTransfer.files); };

  const go = async () => {
    if (!hasInput || ceilBad || areaBad) return;
    setBusy(true);
    setErr(null);
    try {
      let work = b;
      const fields = {
        space_chip: chip, description: desc.trim(),
        ...(areaNum !== null ? { area_pyeong: Math.round(areaNum * 10) / 10 } : {}),
        ...(ceilNum !== null ? { ceiling_m: ceilNum } : {}),
      };
      if (!work) {
        const back = sp.get('return_to') ?? sp.get('return');   // 제안서 PRS3 「조감도 새로 만들기」(옛 링크는 ?return=)
        const origin = back ? { service: 'proposal', return_to: back } : undefined;
        work = await be.create({ ...fields, origin: origin as never, prefill: refVersion ? { products: [], reference_image_version: refVersion } : undefined });
      } else {
        work = await be.patch(work.id, { ...fields, clear_area: areaNum === null, clear_ceiling: ceilNum === null });
      }
      qc.setQueryData(qk.one(work.id), work);
      if (files.length) {
        const up = await uploadAll(files);
        const out = await be.attach(work.id, up.map((f) => f.id));
        setFiles([]);
        nav(out.route, { replace: !id });
        return;
      }
      if (existing.some((f) => f.kind === 'plan')) {
        const plans = await be.plans(work.id);
        const open = plans.items.find((p) => p.status !== 'recognized' || p.check_count > 0);
        if (open) { nav(`/birdseye/${work.id}/space/plan?plan=${open.id}`); return; }
      }
      await be.analyze(work.id);
      await qc.invalidateQueries({ queryKey: qk.one(work.id) });
      nav(`/birdseye/${work.id}/products`, { replace: !id });
    } catch (e) {
      setErr(errText(e));
      toast(errText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <BePage testId="be1" dock={(
      <Dock title="공간 입력" meta="1 / 5" foot={(
        <MainButton onClick={go} disabled={!hasInput || ceilBad || areaBad} busy={busy} testId="be1-next"
          reason={!hasInput ? '공간 설명을 적거나 도면 · 사진을 첨부해 주세요' : '입력값을 확인해 주세요'}>배치될 제품 입력</MainButton>
      )}>
        <div className="be-row" role="radiogroup" aria-label="공간 유형">
          <FieldLabel>공간 유형</FieldLabel>
          {CHIPS.map((c) => <Pill key={c.value} on={chip === c.value} onClick={() => setChip(c.value)} testId={`be1-chip-${c.value}`}>{c.label}</Pill>)}
        </div>
        <div>
          <label htmlFor="be-space" className="wm-sr-only">공간 설명</label>
          <textarea id="be-space" className="be-textarea" maxLength={1000} value={desc} onChange={(e) => setDesc(e.target.value)}
            placeholder="예) 강남 플래그십 스토어 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개." />
        </div>
        <div className="be-grid3">
          <div className="be-field">
            <label htmlFor="be-area">면적</label>
            <div className={areaBad ? 'be-unit be-unit--err' : 'be-unit'}>
              <input id="be-area" inputMode="decimal" placeholder="120" value={area} onChange={(e) => setArea(e.target.value.replace(/[^0-9.]/g, ''))} />
              <span>평</span>
            </div>
            {areaBad && <span className="be-err">면적을 숫자로 적어 주세요</span>}
          </div>
          <div className="be-field">
            <label htmlFor="be-ceil">층고</label>
            <div className={ceilBad ? 'be-unit be-unit--err' : 'be-unit'}>
              <input id="be-ceil" inputMode="decimal" placeholder="4.5" value={ceil} onChange={(e) => setCeil(e.target.value.replace(/[^0-9.]/g, ''))} />
              <span>m</span>
            </div>
            {ceilBad && <span className="be-err">층고는 1.8~20 m 사이로 적어 주세요</span>}
          </div>
          <div className="be-field">
            <span>도면 · 사진</span>
            <button type="button" className={over ? 'be-attach be-attach--over' : 'be-attach'} onClick={() => fileRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop} data-testid="be1-attach">
              <Icon name="upload" size={14} /><span>파일 첨부</span>
            </button>
            <input ref={fileRef} type="file" accept={ACCEPT} multiple hidden data-testid="be1-file" onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
          </div>
        </div>
        {(files.length > 0 || existing.length > 0 || refVersion) && (
          <div className="be-files">
            {refVersion && (
              <span className="be-ref-chip" data-testid="be1-ref">{refThumb ? <img src={refThumb} alt="" /> : <Icon name="image" size={14} />}참조 이미지</span>
            )}
            {existing.map((f) => <span key={f.file_id} className="be-filechip"><Icon name="file" size={13} />{f.name}</span>)}
            {files.map((f, i) => (
              <span key={`${f.name}-${i}`} className="be-filechip"><Icon name="file" size={13} />{f.name}
                <button type="button" aria-label={`${f.name} 빼기`} onClick={() => setFiles((cur) => cur.filter((_, k) => k !== i))}><Icon name="x" size={12} /></button>
              </span>
            ))}
          </div>
        )}
        {err && <div className="be-err" role="alert">{err}</div>}
      </Dock>
    )}>
      <Agent text="조감도를 만들 공간을 알려주세요. 용도, 대략의 면적과 층고, 창·기둥 같은 특징이 있으면 함께 적어주세요. 도면이나 현장 사진을 첨부하면 구조를 더 정확히 반영합니다."
        sub="여러 공간을 한 조감도에 담으려면 공간을 줄 단위로 나눠 적어주세요." />
    </BePage>
  );
}
