/**
 * 자동 저장 입력 — 포커스가 있는 동안은 화면의 글을 그대로 두고(서버가 다듬은 값으로 덮지 않음),
 * 포커스가 없을 때 바깥 값(서버 · 채우기 잡)을 따른다.
 */
import { forwardRef, useEffect, useRef, useState, type InputHTMLAttributes, type Ref, type TextareaHTMLAttributes } from 'react';

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> & { value: string; onText: (v: string) => void };

export const LiveInput = forwardRef(function LiveInput({ value, onText, onFocus, onBlur, ...rest }: InputProps, ref: Ref<HTMLInputElement>) {
  const [local, setLocal] = useState(value);
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setLocal(value); }, [value]);
  return (
    <input ref={ref} {...rest} value={local}
      onFocus={(e) => { focused.current = true; onFocus?.(e); }}
      onBlur={(e) => { focused.current = false; setLocal(value); onBlur?.(e); }}
      onChange={(e) => { setLocal(e.target.value); onText(e.target.value); }} />
  );
});

type AreaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'value' | 'onChange'> & { value: string; onText: (v: string) => void };

export function LiveTextarea({ value, onText, onFocus, onBlur, ...rest }: AreaProps) {
  const [local, setLocal] = useState(value);
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setLocal(value); }, [value]);
  return (
    <textarea {...rest} value={local}
      onFocus={(e) => { focused.current = true; onFocus?.(e); }}
      onBlur={(e) => { focused.current = false; setLocal(value); onBlur?.(e); }}
      onChange={(e) => { setLocal(e.target.value); onText(e.target.value); }} />
  );
}
