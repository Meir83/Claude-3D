"use client";
import { useState, useRef, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled = false, placeholder = "Describe the 3D model you want to create…" }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div className="p-4 border-t border-surface-500 bg-surface-800">
      <div className={clsx(
        "flex items-end gap-2 bg-surface-700 border rounded-xl px-4 py-3 transition-colors",
        disabled ? "border-surface-500 opacity-60" : "border-surface-500 focus-within:border-brand-400"
      )}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          disabled={disabled}
          placeholder={placeholder}
          rows={1}
          className="flex-1 bg-transparent text-surface-100 placeholder:text-surface-400 text-sm
                     resize-none outline-none leading-relaxed max-h-[200px] overflow-y-auto"
        />
        <button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className={clsx(
            "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all",
            value.trim() && !disabled
              ? "bg-brand-400 hover:bg-brand-500 text-white"
              : "bg-surface-600 text-surface-400 cursor-not-allowed"
          )}
        >
          {disabled ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
      <p className="text-xs text-surface-400 mt-2 px-1">
        Shift + Enter for new line · Enter to send
      </p>
    </div>
  );
}
