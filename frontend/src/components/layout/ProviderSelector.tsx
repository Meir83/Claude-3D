"use client";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, Cpu, Wifi, WifiOff, Loader2, Check } from "lucide-react";
import { clsx } from "clsx";
import { api } from "@/lib/api";
import { useWorkspaceStore } from "@/store/workspace";
import { ProviderId, ProvidersMap } from "@/types/api";

// Provider accent colours
const PROVIDER_COLORS: Record<string, string> = {
  claude: "text-brand-400",
  gemini: "text-blue-400",
  ollama: "text-emerald-400",
};

const PROVIDER_ICONS: Record<string, string> = {
  claude: "✦",
  gemini: "✧",
  ollama: "⬡",
};

export function ProviderSelector() {
  const {
    selectedProvider, selectedModel,
    providers, providersLoading,
    setSelectedProvider, setSelectedModel,
    setProviders, setProvidersLoading,
  } = useWorkspaceStore();

  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Load providers on mount
  useEffect(() => {
    setProvidersLoading(true);
    api.getProviders()
      .then(setProviders)
      .catch(() => {/* non-critical */})
      .finally(() => setProvidersLoading(false));
  }, []);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const current = providers?.[selectedProvider];
  const currentModelId = selectedModel ?? current?.default_model;
  const currentModelName = current?.models.find(m => m.id === currentModelId)?.name ?? currentModelId;

  return (
    <div ref={ref} className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        className={clsx(
          "flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all text-sm",
          open
            ? "bg-surface-600 border-surface-400 text-surface-100"
            : "bg-surface-700 border-surface-500 text-surface-200 hover:border-surface-400 hover:text-surface-100"
        )}
      >
        {providersLoading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin text-surface-400" />
        ) : (
          <span className={clsx("text-sm font-medium", PROVIDER_COLORS[selectedProvider])}>
            {PROVIDER_ICONS[selectedProvider]}
          </span>
        )}
        <span className="hidden sm:block font-medium">{current?.name ?? selectedProvider}</span>
        {currentModelName && (
          <span className="hidden md:block text-xs text-surface-400 bg-surface-800 px-1.5 py-0.5 rounded">
            {currentModelName?.split(" ")[0]}
          </span>
        )}
        {current && (
          <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0",
            current.available ? "bg-emerald-400" : "bg-red-400"
          )} title={current.available ? "Available" : "Not available"} />
        )}
        <ChevronDown className={clsx("w-3.5 h-3.5 text-surface-400 transition-transform", open && "rotate-180")} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-surface-800 border border-surface-500 rounded-xl shadow-2xl z-50 overflow-hidden animate-fade-in">
          <div className="px-4 py-3 border-b border-surface-600">
            <p className="text-xs font-semibold text-surface-300 uppercase tracking-wider">AI Provider</p>
          </div>

          {!providers ? (
            <div className="px-4 py-6 text-center text-surface-400 text-sm">
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
              Checking availability…
            </div>
          ) : (
            <div className="p-2">
              {(Object.entries(providers) as [ProviderId, ProvidersMap[ProviderId]][]).map(([id, info]) => (
                <ProviderRow
                  key={id}
                  providerId={id}
                  info={info}
                  isSelected={selectedProvider === id}
                  selectedModel={selectedProvider === id ? currentModelId : null}
                  onSelect={(modelId) => {
                    setSelectedProvider(id, modelId);
                    setOpen(false);
                  }}
                />
              ))}
            </div>
          )}

          <div className="px-4 py-3 border-t border-surface-600 bg-surface-900/50">
            <p className="text-xs text-surface-500 leading-relaxed">
              Ollama runs <span className="text-emerald-400 font-medium">free</span> locally —
              install at <span className="font-mono text-surface-400">ollama.ai</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function ProviderRow({
  providerId, info, isSelected, selectedModel, onSelect,
}: {
  providerId: ProviderId;
  info: ProvidersMap[ProviderId];
  isSelected: boolean;
  selectedModel: string | null | undefined;
  onSelect: (modelId: string) => void;
}) {
  const [expanded, setExpanded] = useState(isSelected);
  const defaultModel = info.models.find(m => m.default) ?? info.models[0];

  return (
    <div className={clsx(
      "rounded-xl mb-1 overflow-hidden border transition-colors",
      isSelected ? "border-surface-400 bg-surface-700" : "border-transparent hover:bg-surface-700/50"
    )}>
      {/* Provider header */}
      <button
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
        onClick={() => {
          setExpanded(e => !e);
          if (!isSelected) onSelect(defaultModel?.id ?? info.default_model);
        }}
      >
        <span className={clsx("text-lg w-6 text-center flex-shrink-0", PROVIDER_COLORS[providerId])}>
          {PROVIDER_ICONS[providerId]}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-surface-100">{info.name}</span>
            {info.free && (
              <span className="text-xs bg-emerald-900/50 border border-emerald-700 text-emerald-400 px-1.5 py-0.5 rounded-full">
                Free
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5">
            {info.available ? (
              <><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-xs text-emerald-400">Available</span></>
            ) : (
              <><WifiOff className="w-3 h-3 text-red-400" /><span className="text-xs text-red-400">
                {info.requires_key ? `Set ${info.key_env}` : "Ollama not running"}
              </span></>
            )}
          </div>
        </div>
        {isSelected && <Check className="w-4 h-4 text-brand-400 flex-shrink-0" />}
        <ChevronDown className={clsx("w-3.5 h-3.5 text-surface-500 transition-transform flex-shrink-0",
          expanded && "rotate-180"
        )} />
      </button>

      {/* Model list */}
      {expanded && info.models.length > 0 && (
        <div className="px-3 pb-2 space-y-0.5">
          {info.models.map(model => (
            <button
              key={model.id}
              onClick={() => onSelect(model.id)}
              className={clsx(
                "w-full text-left px-3 py-1.5 rounded-lg text-xs transition-colors flex items-center justify-between",
                selectedModel === model.id && isSelected
                  ? "bg-brand-500/20 text-brand-300"
                  : "text-surface-300 hover:bg-surface-600 hover:text-surface-100"
              )}
            >
              <span className="font-mono">{model.name}</span>
              {model.default && (
                <span className="text-surface-500 ml-2 flex-shrink-0">default</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
