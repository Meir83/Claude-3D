import { Loader2 } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

const SIZE = { sm: "w-4 h-4", md: "w-6 h-6", lg: "w-8 h-8" };

export function LoadingSpinner({ size = "md", className, label }: Props) {
  return (
    <div className={clsx("flex items-center gap-2 text-surface-300", className)}>
      <Loader2 className={clsx(SIZE[size], "animate-spin text-brand-400")} />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
