"""도구 호출 대체(LLM_SUPPORTS_TOOLS=false) — ReAct 식 텍스트 규약으로 tool_calls 를 만든다.

모델에게 도구 목록과 규약을 시스템 지시로 주고, 답에서

    Action: <도구 이름>
    Action Input: {"인자": "값"}

블록을 찾아 tool_calls 로 바꾼다. 도구 없이 답하면 `Final Answer: …` 뒤 문장이 content 가 된다.
앞선 대화의 tool_calls · tool 결과는 같은 규약의 텍스트(Action … / Observation …)로 바꿔 넣는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from winmate_common.ids import new_id

_ACTION = re.compile(r"^\s*Action\s*:\s*(.+?)\s*$", re.M | re.I)
_INPUT = re.compile(r"Action\s*Input\s*:\s*", re.I)
_FINAL = re.compile(r"Final\s*Answer\s*:\s*", re.I)


def system_prompt(tools: list[dict[str, Any]], tool_choice: str | None) -> str:
    lines = [
        "You can use tools. Each tool takes a JSON object of arguments that must follow its JSON Schema.",
        "",
        "Tools:",
    ]
    for t in tools:
        lines.append(f"- name: {t['name']}")
        if t.get("description"):
            lines.append(f"  description: {t['description']}")
        lines.append(f"  parameters: {json.dumps(t.get('parameters') or {'type': 'object'}, ensure_ascii=False, separators=(',', ':'))}")
    lines += [
        "",
        "To call tools, reply with ONLY these lines (one block per call, the JSON on one line):",
        "Action: <tool name>",
        "Action Input: <JSON object>",
        "",
        "After you receive the Observation results, continue. When you can answer without more tools, reply with:",
        "Final Answer: <your answer>",
    ]
    if tool_choice and tool_choice not in ("auto", "none"):
        if tool_choice in ("required", "any"):
            lines.append("You MUST call at least one tool now.")
        else:
            lines.append(f"You MUST call the tool `{tool_choice}` now.")
    return "\n".join(lines)


def render_call(name: str, arguments: dict[str, Any]) -> str:
    return f"Action: {name}\nAction Input: {json.dumps(arguments, ensure_ascii=False, separators=(',', ':'))}"


def render_observation(name: str | None, call_id: str | None, content: str) -> str:
    tag = " ".join(x for x in (name or "", f"id={call_id}" if call_id else "") if x)
    return f"Observation [{tag}]: {content}" if tag else f"Observation: {content}"


@dataclass
class Parsed:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def parse(text: str, tool_names: set[str]) -> Parsed:
    """모델 답에서 Action 블록 → tool_calls. 없으면 Final Answer(또는 전체)를 content 로."""
    text = text or ""
    calls: list[dict[str, Any]] = []
    first_action_at: int | None = None
    dec = json.JSONDecoder()
    for m in _ACTION.finditer(text):
        name = m.group(1).strip().strip("`'\"")
        after = text[m.end():]
        im = _INPUT.search(after)
        args: Any = {}
        if im is not None:
            rest = after[im.end():].lstrip()
            if rest.startswith("```"):
                rest = re.sub(r"^```(?:json)?\s*", "", rest)
            try:
                args, _ = dec.raw_decode(rest)
            except ValueError:
                args = {}
            # 다음 Action 보다 뒤에 있는 Input 은 이 Action 의 것이 아니다
            nxt = _ACTION.search(after)
            if nxt is not None and nxt.start() < im.start():
                args = {}
        if name not in tool_names:
            continue
        if first_action_at is None:
            first_action_at = m.start()
        calls.append({"id": new_id("call"), "name": name, "arguments": args if isinstance(args, dict) else {"input": args}})
    if calls:
        thought = text[: first_action_at or 0].strip()
        thought = re.sub(r"^\s*Thought\s*:\s*", "", thought, flags=re.I)
        return Parsed(content=thought, tool_calls=calls)
    fm = _FINAL.search(text)
    content = text[fm.end():].strip() if fm else text.strip()
    return Parsed(content=content)
