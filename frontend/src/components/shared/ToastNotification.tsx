"use client";
import { useEffect } from "react";
import { XCircle, X } from "lucide-react";
import { useWorkspaceStore } from "@/store/workspace";

export function ToastNotification() {
  const { toastError, setToastError } = useWorkspaceStore();

  useEffect(() => {
    if (!toastError) return;
    const timer = setTimeout(() => setToastError(null), 6000);
    return () => clearTimeout(timer);
  }, [toastError, setToastError]);

  if (!toastError) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
      <div className="flex items-start gap-3 bg-red-950 border border-red-800 text-red-200 rounded-xl px-4 py-3 shadow-xl max-w-sm">
        <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
        <p className="text-sm leading-snug flex-1">{toastError}</p>
        <button
          onClick={() => setToastError(null)}
          className="text-red-400 hover:text-red-200 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
