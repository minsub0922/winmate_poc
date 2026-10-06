/**
 * 기본 옵션 내보내기(§4.17 · §4.19 — 한국어 · 현재 마스터 · 「[확정 필요] 표시 남기기」) → 끝나면 내려받기.
 * 생성 결과에 이미 그 형식 파일이 있으면 바로 내려받는다.
 */
import { useState } from 'react';
import { toast } from '@/ui';
import { getExport, postExport } from '../api/proposal';
import { errText, jobErrText } from '../api/http';
import { useJobEvents } from '../api/jobs';

export function download(url: string, name?: string) {
  const a = document.createElement('a');
  a.href = url;
  if (name) a.download = name;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  a.remove();
}

export function useQuickExport(id: string | undefined) {
  const [job, setJob] = useState<{ jobId: string; exportId: string | null; format: 'pptx' | 'pdf' } | null>(null);
  const ev = useJobEvents(job?.jobId, {
    onDone: async (j) => {
      const cur = job;
      setJob(null);
      if (!id || !cur) return;
      if (j.status !== 'succeeded') { toast(jobErrText(j.error, '파일을 만들지 못했어요. 다시 시도해 주세요')); return; }
      const xid = cur.exportId ?? (j.result?.export_id as string | undefined) ?? null;
      if (!xid) return;
      try {
        const rec = await getExport(id, xid);
        const f = rec.files?.find((x) => x.format === cur.format) ?? rec.files?.[0];
        if (f) download(f.url, f.name);
      } catch (e) { toast(errText(e)); }
    },
  });
  const run = async (format: 'pptx' | 'pdf', direct?: string | null, name?: string) => {
    if (!id) return;
    if (direct) { download(direct, name); return; }
    try {
      const r = await postExport(id, { formats: [format], lang: 'ko', tbd_mode: 'keep_marks' });
      setJob({ jobId: r.job_id, exportId: r.export_id ?? null, format });
    } catch (e) { toast(errText(e)); }
  };
  return { run, busy: job?.format ?? null, progress: ev.progress };
}
