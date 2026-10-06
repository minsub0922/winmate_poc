/** 말로 수정(spec_revise) 공용 훅 — SP3 · SP3W · SP4 입력창(06-spec §7.5) */
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useJob } from '@/api/jobs';
import { toast } from '@/ui';
import { downloadFile, errText, sendMessage, useSheetCache, waitExport } from './api';

type Ctx = 'result' | 'warnings' | 'export';

export function useRevise(sheetId: string, context: Ctx) {
  const nav = useNavigate();
  const cache = useSheetCache();
  const [job, setJob] = useState<string | null>(null);
  const [userText, setUserText] = useState<string | null>(null);
  const [reply, setReply] = useState<string | null>(null);

  useJob(job, {
    onDone: async (j) => {
      setJob(null);
      await cache.refresh(sheetId);
      void cache.refreshWarnings(sheetId);
      if (j.status !== 'succeeded') {
        if (j.status === 'failed') toast(j.error?.message ?? '요청을 처리하지 못했어요.');
        return;
      }
      const r = (j.result ?? {}) as { reply?: string | null; navigate?: string | null; needs_clarification?: string | null;
        exports?: Array<{ export_id: string; format: string }>; applied_ops?: string[] };
      setReply(r.needs_clarification || r.reply || null);
      for (const x of r.exports ?? []) {
        waitExport(sheetId, x.export_id)
          .then((rec) => { if (rec.status === 'done' && rec.file_id) downloadFile(rec.file_id, rec.filename); else toast(rec.error ?? '파일을 만들지 못했어요.'); })
          .catch((e) => toast(errText(e)));
      }
      const from = context === 'export' ? 'export' : 'result';
      if (r.navigate === 'SP3W') nav(`/spec/${sheetId}/warnings`);
      else if (r.navigate === 'SP2L') nav(`/spec/${sheetId}/format?from=${from}`);
      else if (r.navigate === 'SP1C') nav(`/spec/${sheetId}/find`);
    },
  });

  const send = async (text: string) => {
    setUserText(text);
    setReply(null);
    try {
      const r = await sendMessage(sheetId, text, context);
      if (r.job_id) setJob(r.job_id);
    } catch (e) {
      toast(errText(e));
      setUserText(null);
    }
  };

  return { send, busy: !!job, userText, reply };
}
