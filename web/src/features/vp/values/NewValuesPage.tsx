/**
 * 새 VP(가치 · 고객의 니즈) 시작 — `/vp/values/new?sb=&title=&text=`
 * 사전 작업 Storyboard 고르기(보드 Gate)는 Storyboard 흐름이 들어오면 그 화면으로 바뀐다. 지금은 요구 문장으로 시작하고,
 * 제품 · 솔루션 후보는 KB(S1 · 공간별 후보)에서 찾아 다음 화면에서 고르게 한다.
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import { FlowFooter, FlowHead, FlowScreen, LinkedStoryboardBar, TextArea, Input, toast } from '@/ui';
import { createValueMap } from './api';
import './values.css';

export function NewValuesPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [title, setTitle] = useState(sp.get('title') ?? '');
  const [text, setText] = useState(sp.get('text') ?? '');
  const [busy, setBusy] = useState(false);
  const sb = sp.get('sb');
  useShellPage({ section: 'Value Proposition', title: '새 VP', hasTask: true, stepper: { steps: ['Storyboard', '가치 · 고객의 니즈'], current: 1 } });
  const start = async () => {
    setBusy(true);
    try {
      const d = await createValueMap({ title: title.trim() || '새 VP', sb_id: sb, context_text: text.trim() || null, select_all: true });
      nav(`/vp/values/${d.id}`, { replace: true });
    } catch (e) { toast((e as Error).message || '만들지 못했어요.'); setBusy(false); }
  };
  return (
    <FlowScreen pad="22px 120px" gap={14} bar={<LinkedStoryboardBar chips={sb ? [{ id: sb, name: title || sb, done: ['rq', 'dss'], current: 'vp' }] : []} emptyText="연결된 Storyboard가 없어요 · 요구 문장으로 시작해요" />}>
      <FlowHead title="어떤 제안의 가치를 정리할까요?" desc="요구 문장을 넣으면 공간별 제품 · 솔루션 후보를 KB에서 찾아 와요. 다음 화면에서 고르고 바꿀 수 있어요." />
      <label className="vv-editlab vv-editlab--full">제목<Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 용산 AI Ready 오피스" /></label>
      <label className="vv-editlab vv-editlab--full">요구 · Storyboard 요약
        <TextArea value={text} onChange={(e) => setText(e.target.value)} rows={8}
          placeholder="예: 용산 업무시설 재개발 · 로비 미디어월과 안내 사이니지 · 회의실 전자칠판 · 에너지 20% 절감 실측 증빙" />
      </label>
      <span style={{ flex: 1 }} />
      <FlowFooter back={{ to: '/vp', label: '목록' }} summary={text.trim() ? '제품 · 솔루션 후보를 KB에서 찾아요' : '요구 문장 없이 시작하면 제품 · 솔루션을 직접 골라요'}
        primary={{ label: '가치 적기 시작', onClick: start, busy }} />
    </FlowScreen>
  );
}
