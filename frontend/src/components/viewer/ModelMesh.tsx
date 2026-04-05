"use client";
import { useEffect, useRef } from "react";
import { useLoader, useThree } from "@react-three/fiber";
import { STLLoader } from "three/addons/loaders/STLLoader.js";
import * as THREE from "three";

interface Props {
  url: string;
  wireframe?: boolean;
}

export function ModelMesh({ url, wireframe = false }: Props) {
  const geometry = useLoader(STLLoader, url);
  const { camera, controls } = useThree();
  const meshRef = useRef<THREE.Mesh>(null);

  // Centre and scale on load
  useEffect(() => {
    if (!geometry || !meshRef.current) return;

    geometry.computeBoundingBox();
    const box = geometry.boundingBox!;
    const center = new THREE.Vector3();
    box.getCenter(center);
    geometry.translate(-center.x, -center.y, -center.z);

    const size = new THREE.Vector3();
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = maxDim > 0 ? 5 / maxDim : 1;
    meshRef.current.scale.setScalar(scale);

    // Position camera
    const dist = maxDim * scale * 2;
    camera.position.set(dist, dist * 0.7, dist);
    camera.lookAt(0, 0, 0);

  }, [geometry, camera]);

  return (
    <mesh ref={meshRef} geometry={geometry} castShadow receiveShadow>
      <meshStandardMaterial
        // Matches preview.py baseColorFactor=[0.42, 0.62, 0.92]
        color={new THREE.Color(0.42, 0.62, 0.92)}
        metalness={0.1}
        roughness={0.6}
        wireframe={wireframe}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
