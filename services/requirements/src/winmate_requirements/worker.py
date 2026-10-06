"""requirements 워커 — Redis 큐(wm:q:requirements) 소비. `python -m winmate_requirements.worker`.

잡 종류(§7.1)
- rq.fill           파일 → 폼(LangGraph rq_fill)
- rq.deep.analyze   보강할 곳 찾기(LangGraph rq_deep_analyze)
- rq.reply.analyze  고객 답변 → 바뀔 곳(LangGraph rq_reply_analyze)
- rq.short          항목 short · short_title(화면 없음)
- rq.export         정의서 DOCX · PDF(export 서비스)
"""
from __future__ import annotations

from winmate_common.jobs import JobContext, run_worker

from . import deep, exports, fill, replies, shorts


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


HANDLERS = {
    "noop": _noop,
    "rq.fill": fill.handle_fill,
    "rq.deep.analyze": deep.handle_analyze,
    "rq.reply.analyze": replies.handle_analyze,
    "rq.short": shorts.handle_short_job,
    "rq.export": exports.handle_export,
}


def main() -> None:
    run_worker("requirements", HANDLERS)


if __name__ == "__main__":
    main()
