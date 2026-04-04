"use client";
import { useCallback, useEffect, useRef, useState } from "react";

interface UseResizePanelOptions {
  initialPercent?: number;
  minPercent?: number;
  maxPercent?: number;
}

export function useResizePanel({
  initialPercent = 40,
  minPercent = 25,
  maxPercent = 70,
}: UseResizePanelOptions = {}) {
  const [leftPercent, setLeftPercent] = useState(initialPercent);
  const isDragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const onMouseDown = useCallback(() => {
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = (x / rect.width) * 100;
      setLeftPercent(Math.min(maxPercent, Math.max(minPercent, pct)));
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [minPercent, maxPercent]);

  return { leftPercent, containerRef, onMouseDown };
}
