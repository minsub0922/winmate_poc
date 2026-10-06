/**
 * 셸 단독 테스트용 개발 화면(00-shell §8.0 [제안]): `/_dev/shell?task=1&accepts=product,solution,image,case&added=<ref,…>`
 * 작업 맥락을 흉내 내고 onAdd · onAttach · onDrop · onOneClick 호출을 기록한다(`window.__wmShellLog`, 화면 아래 로그).
 * 쿼리: task=1 · accepts=… · work=MI,SP(acceptsWork) · added=… · fail=1(onAdd 실패) · noattach=1 · group=<기능 key>
 *       · steps=a,b,c|proposal · current=2 · complete=1 · autoFrom=4 · oneClick=1 · open=1 · vertical=kr_retail_fnb:유통/요식
 * 운영 빌드에서 빼려면 VITE_WM_DEVTOOLS=0 으로 빌드한다.
 */
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { DropZone, Section, type DragPayload, type DragType } from '@/ui';
import { useShellPage } from '../ShellContext';
import type { FeatureCode, StepperConfig } from '../types';

declare global {
  interface Window { __wmShellLog?: Array<{ kind: string; [k: string]: unknown }> }
}

const PROPOSAL_STEPS = ['고객 · 프로젝트', '제안서 유형', '시트 구성', '섹션 작성', '디자인 템플릿', 'PPTX 생성'];

function log(entry: { kind: string; [k: string]: unknown }) {
  window.__wmShellLog = [...(window.__wmShellLog ?? []), entry];
}

export default function DevShell() {
  const [sp] = useSearchParams();
  const list = (k: string) => (sp.get(k) ?? '').split(',').map((s) => s.trim()).filter(Boolean);
  const task = sp.get('task') === '1';
  const accepts = list('accepts') as DragType[];
  const work = list('work') as FeatureCode[];
  const fail = sp.get('fail') === '1';
  const [added, setAdded] = useState<string[]>(() => list('added'));
  const [entries, setEntries] = useState<Array<{ kind: string; [k: string]: unknown }>>([]);
  const push = (e: { kind: string; [k: string]: unknown }) => { log(e); setEntries((x) => [...x, e]); };

  const stepsRaw = sp.get('steps');
  const stepper: StepperConfig | undefined = useMemo(() => {
    if (!stepsRaw) return undefined;
    const steps = stepsRaw === 'proposal' ? PROPOSAL_STEPS : stepsRaw.split(',');
    return {
      steps,
      current: Number(sp.get('current') ?? 1),
      complete: sp.get('complete') === '1',
      autoFrom: Number(sp.get('autoFrom') ?? 0),
      oneClickOpen: sp.get('open') === '1',
      oneClick: sp.get('oneClick') === '1' ? { onRun: (o) => push({ kind: 'oneClick', ...o }) } : undefined,
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepsRaw, sp]);
  const vertical = sp.get('vertical');

  useShellPage({
    section: '셸 개발',
    title: task ? '작업 맥락 흉내' : '작업 없음',
    hasTask: task,
    accepts,
    acceptsWork: work.length ? work : undefined,
    added,
    sidebarGroup: sp.get('group') ?? undefined,
    taskContext: vertical ? { verticalId: vertical.split(':')[0], verticalName: vertical.split(':')[1] } : undefined,
    onAdd: task ? async (type, refs) => {
      push({ kind: 'onAdd', type, refs });
      if (fail) throw new Error('fail');
      setAdded((a) => [...a, ...refs.filter((r) => !a.includes(r))]);
      return { added: refs };
    } : undefined,
    onAttach: task && sp.get('noattach') !== '1' ? (images) => { push({ kind: 'onAttach', count: images.length, images }); } : undefined,
    stepper,
  });

  const onDrop = async (p: DragPayload) => {
    push({ kind: 'onDrop', payload: p });
    if (fail) return false;
    setAdded((a) => (a.includes(p.ref) ? a : [...a, p.ref]));
    return { note: '개발 화면에 기록됨' };
  };

  return (
    <div className="sh-dev">
      <Section title="셸 개발 화면" desc={task ? `작업 있음 · accepts=${accepts.join(',') || '없음'}` : '작업 없음'}>
        <span className="wm-small wm-muted">상단바 팝오버 4종 · 상세 시트 · 끌어서 추가를 이 화면에서 시험한다. onAdd · onAttach · onDrop 호출은 아래에 기록된다.</span>
        {accepts.length > 0 && (
          <DropZone accept={accepts} acceptWork={work.length ? work : undefined} workLabel={work[0]} onDrop={onDrop}
            onUndo={(p) => { push({ kind: 'undo', ref: p.ref }); setAdded((a) => a.filter((r) => r !== p.ref)); }}
            dragSub={() => '→ 셸 개발 화면 · 호출이 로그에 남습니다'} />
        )}
      </Section>
      <Section title="added" flat><pre data-testid="dev-added">{JSON.stringify(added)}</pre></Section>
      <Section title="호출 기록" flat><pre data-testid="dev-log">{entries.map((e) => JSON.stringify(e)).join('\n') || '(없음)'}</pre></Section>
    </div>
  );
}
