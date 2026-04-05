"use client";
import { clsx } from "clsx";

interface Props {
  onMouseDown: () => void;
}

export function ResizableDivider({ onMouseDown }: Props) {
  return (
    <div
      onMouseDown={onMouseDown}
      className="group relative w-1 flex-shrink-0 cursor-col-resize bg-surface-500 hover:bg-brand-400/60 transition-colors"
    >
      {/* Grab handle indicator */}
      <div className="absolute inset-y-0 -left-1 -right-1" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                      w-1 h-8 rounded-full bg-surface-400 group-hover:bg-brand-400 transition-colors opacity-60" />
    </div>
  );
}
