"use client";
import { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import { ErrorBoundary } from "react-error-boundary";
import { ViewerEnvironment } from "./ViewerEnvironment";
import { ModelMesh } from "./ModelMesh";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { AlertTriangle, Maximize2, Grid3X3, Layers } from "lucide-react";

interface Props {
  stlUrl: string;
}

export function ModelViewer3D({ stlUrl }: Props) {
  const [wireframe, setWireframe] = useState(false);
  const [cameraKey, setCameraKey] = useState(0);

  return (
    <div className="relative w-full h-full">
      <ErrorBoundary FallbackComponent={ViewerError}>
        <Canvas
          shadows
          gl={{ antialias: true, alpha: false }}
          style={{ background: "#0d0f14" }}
        >
          <PerspectiveCamera key={cameraKey} makeDefault fov={35} />
          <ViewerEnvironment />
          <Suspense fallback={null}>
            <ModelMesh url={stlUrl} wireframe={wireframe} />
          </Suspense>
          <OrbitControls
            enablePan
            enableZoom
            enableRotate
            dampingFactor={0.1}
            enableDamping
          />
        </Canvas>

        {/* Overlay controls */}
        <div className="absolute bottom-4 right-4 flex flex-col gap-2">
          <ViewerButton
            onClick={() => setCameraKey((k) => k + 1)}
            title="Reset camera"
          >
            <Maximize2 className="w-4 h-4" />
          </ViewerButton>
          <ViewerButton
            onClick={() => setWireframe((w) => !w)}
            title="Toggle wireframe"
            active={wireframe}
          >
            <Grid3X3 className="w-4 h-4" />
          </ViewerButton>
        </div>

        {/* Loading overlay */}
        <Suspense fallback={
          <div className="absolute inset-0 flex items-center justify-center bg-surface-900/80">
            <LoadingSpinner size="md" label="Loading model…" />
          </div>
        }>
          {null}
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}

function ViewerButton({
  onClick, title, active, children,
}: {
  onClick: () => void;
  title: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`w-9 h-9 rounded-lg border flex items-center justify-center transition-colors
        ${active
          ? "bg-brand-500/20 border-brand-400 text-brand-400"
          : "bg-surface-800/90 border-surface-500 text-surface-300 hover:text-surface-100 hover:border-surface-400"
        }`}
    >
      {children}
    </button>
  );
}

function ViewerError() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-surface-300">
      <AlertTriangle className="w-8 h-8 text-amber-400" />
      <p className="text-sm">Failed to render 3D model</p>
      <p className="text-xs text-surface-400">Check the preview image instead</p>
    </div>
  );
}
