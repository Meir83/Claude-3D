"use client";
import { Grid } from "@react-three/drei";

/**
 * Scene lighting and ground grid matching preview.py's three-point setup.
 */
export function ViewerEnvironment() {
  return (
    <>
      {/* Ambient */}
      <ambientLight color="#ffffff" intensity={0.3} />

      {/* Three-point lighting matching preview.py directions */}
      <directionalLight position={[1, 1, 1]} color="#ffffff" intensity={2.5} />
      <directionalLight position={[-1, 0.5, 0.5]} color="#ffffff" intensity={2.5} />
      <directionalLight position={[0, -1, 1]} color="#ffffff" intensity={2.5} />

      {/* Ground grid */}
      <Grid
        position={[0, -0.01, 0]}
        args={[20, 20]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#2e3548"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#3d4560"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />
    </>
  );
}
