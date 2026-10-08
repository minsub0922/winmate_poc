/**
 * 새 공간 시나리오(공간 → 시나리오 → 장면) 시작 — `/scenario/spaces/new?sb=&title=&text=`
 * 사전 작업 Storyboard 고르기(보드 Gate)는 Storyboard 흐름이 들어오면 그 화면으로 바뀐다. 지금은 요구 문장으로 시작하고,
 * 공간 · 제품은 KB(S1)에서 찾아 다음 화면에서 고치게 한다.
 */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useShellPage } from '@/shell/ShellContext';
import { FlowFooter, FlowHead, FlowScreen, Input, LinkedStoryboardBar, TextArea, toast } from '@/ui';
import { createSpaceSet } from './api';
import './spaces.css';

export function NewSpacesPage() {
  const [sp] = useSearchParams();
  const nav = useNavigate();
  const [title, setTitle] = useState(sp.get('title') ?? '');
  const [text, setText] = useState(sp.get('text') ?? '');
  const [busy, setBusy] = useState(false);
  const sb = sp.get('sb');
  useShellPage({ section: '공간 시나리오 생성', title: '새 공간 시나리오', hasTask: true, stepper: { steps: ['Storyboard', '공간 · 시나리오'], current: 1 } });
  const start = async () => {
    setBusy(true);
    try {
      const d = await createSpaceSet({ title: title.trim() || '새 공간 시나리오', sb_id: sb, context_text: text.trim() || null });
      nav(`/scenario/spaces/${d.id}`, { replace: true });
    } catch (e) { toast((e as Error).message || '만들지 못했어요.'); setBusy(false); }
  };
  return (
    <FlowScreen pad="22px 120px" gap={14} bar={<LinkedStoryboardBar chips={sb ? [{ id: sb, name: title || sb, done: ['rq', 'dss'], current: 'sc' }] : []} emptyText="연결된 Storyboard가 없어요 · 요구 문장으로 시작해요" />}>
      <FlowHead title="어떤 공간의 시나리오를 쓸까요?" desc="요구 문장을 넣으면 공간과 공간별 제품 · 솔루션을 KB에서 찾아 와요. 다음 화면에서 공간 · 제품을 고치고 시나리오를 써요." />
      <label className="vv-editlab vv-editlab--full" style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11.5, fontWeight: 700, color: 'var(--wm-text-muted)' }}>제목
        <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 용산 AI Ready 오피스" /></label>
      <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11.5, fontWeight: 700, color: 'var(--wm-text-muted)' }}>요구 · Storyboard 요약
        <TextArea value={text} onChange={(e) => setText(e.target.value)} rows={8} placeholder="예: 로비 미디어월 · 안내 사이니지 · 회의실 전자칠판 · 중앙관제실 비디오월 · 공용공간 센서" /></label>
      <span style={{ flex: 1 }} />
      <FlowFooter back={{ to: '/scenario', label: '목록' }} summary={text.trim() ? '공간 · 제품을 KB에서 찾아요' : '요구 문장 없이 시작하면 공간 하나로 시작해요'}
        primary={{ label: '시나리오 쓰기 시작', onClick: start, busy }} />
    </FlowScreen>
  );
}
