/**
 * 3D rotating polyhedron rendered via React Three Fiber.
 *
 * Each agent gets a unique shape (dodecahedron, icosahedron, etc.) with a
 * color-matched wireframe. Three visual states:
 *   - Active (working): spins, emissive glow pulse
 *   - Thinking: lit up, scale-pulse (breathing), minimal spin
 *   - Idle: dimmed, slow rotation
 */

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";

import { MathUtils } from "three";
import type { Group, Mesh, MeshStandardMaterial } from "three";
import { useTheme } from "@/hooks/useTheme";
import type { AgentShape } from "./swarm-constants";

type AgentVisualState = "active" | "thinking" | "idle";

interface ShapeProps {
  shape: AgentShape;
  color: string;
  visualState: AgentVisualState;
  isDark: boolean;
}

/** The spinning mesh inside the Canvas. */
function SpinningShape({ shape, color, visualState, isDark }: ShapeProps) {
  const groupRef = useRef<Group>(null);
  const meshRef = useRef<Mesh>(null);
  const wireRef = useRef<Mesh>(null);
  const wireMat = useRef<MeshStandardMaterial>(null);
  const elapsed = useRef(0);

  const isLit = visualState !== "idle";

  useFrame((_, delta) => {
    elapsed.current += delta;

    // --- Rotation speed ---
    // Active: full spin. Thinking: near-still. Idle: slow drift.
    const speed =
      visualState === "active" ? 1 :
      visualState === "thinking" ? 0.08 :
      0.3;

    // --- Scale ---
    if (groupRef.current) {
      let target: number;
      if (visualState === "thinking") {
        // Breathing pulse: oscillate between 0.92 and 1.0
        const breath = Math.sin(elapsed.current * 2.8);
        target = 0.96 + 0.04 * breath;
      } else if (visualState === "active") {
        target = 1;
      } else {
        target = 0.75;
      }
      const current = groupRef.current.scale.x;
      const next = MathUtils.lerp(current, target, 1 - Math.pow(0.02, delta));
      groupRef.current.scale.setScalar(next);
    }

    // --- Rotation ---
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * speed * 0.4;
      meshRef.current.rotation.y += delta * speed * 0.6;
    }
    if (wireRef.current) {
      wireRef.current.rotation.x = meshRef.current?.rotation.x ?? 0;
      wireRef.current.rotation.y = meshRef.current?.rotation.y ?? 0;
    }

    // --- Wireframe emissive ---
    if (wireMat.current) {
      const sin = Math.sin(elapsed.current * 2.5);
      if (visualState === "active") {
        // Working: standard emissive glow pulse
        if (isDark) {
          wireMat.current.emissiveIntensity = 0.6 + 0.6 * sin;
          wireMat.current.opacity = 0.8 + 0.2 * sin;
        } else {
          wireMat.current.emissiveIntensity = 0.15 + 0.2 * sin;
          wireMat.current.opacity = 0.75 + 0.15 * sin;
        }
      } else if (visualState === "thinking") {
        // Thinking: slower, deeper breathing glow
        const breathSin = Math.sin(elapsed.current * 1.8);
        if (isDark) {
          wireMat.current.emissiveIntensity = 0.4 + 0.5 * breathSin;
          wireMat.current.opacity = 0.7 + 0.2 * breathSin;
        } else {
          wireMat.current.emissiveIntensity = 0.1 + 0.18 * breathSin;
          wireMat.current.opacity = 0.65 + 0.15 * breathSin;
        }
      } else {
        // Idle: static
        wireMat.current.emissiveIntensity = isDark ? 0.35 : 0.08;
        wireMat.current.opacity = isDark ? 0.6 : 0.7;
      }
    }
  });

  const geometry = getGeometry(shape);

  return (
    <group ref={groupRef}>
      {/* Solid semi-transparent fill */}
      <mesh ref={meshRef}>
        {geometry}
        <meshStandardMaterial
          color={color}
          transparent
          opacity={isLit
            ? (isDark ? 0.2 : 0.28)
            : (isDark ? 0.12 : 0.18)}
          depthWrite={false}
        />
      </mesh>

      {/* Wireframe overlay — emissive pulses when lit */}
      <mesh ref={wireRef}>
        {geometry}
        <meshStandardMaterial
          ref={wireMat}
          color={color}
          wireframe
          emissive={color}
          emissiveIntensity={isDark ? 0.35 : 0.08}
          transparent
          opacity={isDark ? 0.6 : 0.7}
        />
      </mesh>
    </group>
  );
}

/** Returns a JSX geometry element for the given shape type. */
function getGeometry(shape: AgentShape) {
  switch (shape) {
    case "dodecahedron":
      return <dodecahedronGeometry args={[0.95, 0]} />;
    case "icosahedron":
      return <icosahedronGeometry args={[0.95, 0]} />;
    case "octahedron":
      return <octahedronGeometry args={[0.95, 0]} />;
    case "box":
      return <boxGeometry args={[1.2, 1.2, 1.2]} />;
    case "tetrahedron":
      return <tetrahedronGeometry args={[1.05, 0]} />;
    case "gem":
      return <icosahedronGeometry args={[0.95, 1]} />;
    case "cone":
      return <coneGeometry args={[0.85, 1.3, 6]} />;
  }
}

// ---------------------------------------------------------------------------
// Public component — wraps Canvas with transparent background
// ---------------------------------------------------------------------------

interface AgentPolyhedronProps {
  shape: AgentShape;
  color: string;
  status: AgentVisualState;
}

export function AgentPolyhedron({ shape, color, status }: AgentPolyhedronProps) {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  const isLit = status !== "idle";

  return (
    <div
      style={{
        position: "absolute",
        inset: -40,
        pointerEvents: "none",
      }}
    >
      <Canvas
        gl={{ alpha: true, antialias: true }}
        camera={{ position: [0, 0, 3.2], fov: 50 }}
        resize={{ offsetSize: true }}
        style={{ background: "transparent" }}
      >
      <ambientLight intensity={isDark
        ? (isLit ? 0.8 : 0.5)
        : (isLit ? 1.4 : 1.0)} />
      <pointLight
        position={[3, 3, 4]}
        intensity={isDark
          ? (isLit ? 1.5 : 0.8)
          : (isLit ? 1.0 : 0.6)}
        color={color}
      />
      <pointLight
        position={[-3, -2, 3]}
        intensity={isDark
          ? (isLit ? 0.6 : 0.3)
          : (isLit ? 0.8 : 0.5)}
        color={isDark ? "#ffffff" : "#d0d0d0"}
      />
      <SpinningShape shape={shape} color={color} visualState={status} isDark={isDark} />
    </Canvas>
    </div>
  );
}
