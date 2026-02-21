/**
 * Animated agent circle for the swarm visualization.
 *
 * - Active (working): full opacity, spinning 3D shape
 * - Thinking: full opacity, pulsing 3D shape (no spin)
 * - Idle: muted, smaller
 * - Smooth transitions between states (0.5s)
 * - Draggable with spring-back to original position
 */

import { useRef, useMemo } from "react";
import { motion, useMotionValue, animate } from "framer-motion";
import {
  getAgentConfig,
  NODE_SIZE_ACTIVE,
  type NodeSizes,
} from "./swarm-constants";
import { AgentPolyhedron } from "./AgentPolyhedron";
import { useTheme } from "@/hooks/useTheme";

/** Derive a stable number from an agent name for staggered animations. */
function nameHash(name: string): number {
  let h = 0;
  for (let i = 0; i < name.length; i++) {
    h = (h * 31 + name.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

interface AgentNodeProps {
  name: string;
  status: "active" | "idle" | "thinking";
  x: number;
  y: number;
  /** Dynamic sizes based on container. Falls back to hardcoded constants. */
  nodeSizes?: NodeSizes;
  onClick: () => void;
}

export function AgentNode({
  name,
  status,
  x,
  y,
  nodeSizes,
  onClick,
}: AgentNodeProps) {
  const { theme } = useTheme();
  const isDark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);

  const config = getAgentConfig(name);
  // Both "active" and "thinking" are visually lit up (not dimmed)
  const isLit = status !== "idle";
  const activeSize = nodeSizes?.active ?? NODE_SIZE_ACTIVE;
  const fontSize = nodeSizes?.fontSize ?? 14;
  const labelSize = nodeSizes?.labelSize ?? 10;

  // Motion values for drag — we animate the spring-back manually so fling
  // velocity carries through as overshoot before bouncing home.
  const dragX = useMotionValue(0);
  const dragY = useMotionValue(0);

  // Drag tracking — prevent onClick from firing after a drag release.
  const dragging = useRef(false);

  // Staggered float timing so agents bob independently.
  const floatDuration = useMemo(() => 3 + (nameHash(name) % 20) / 10, [name]);
  const floatDelay = useMemo(() => (nameHash(name) % 10) / 10, [name]);

  return (
    <motion.div
      className="absolute flex items-center justify-center"
      style={{
        left: x,
        top: y,
        x: dragX,
        y: dragY,
        width: activeSize,
        height: activeSize,
        marginLeft: -activeSize / 2,
        marginTop: -activeSize / 2,
        cursor: "grab",
      }}
      drag
      dragMomentum={false}
      whileDrag={{ scale: 1.12, cursor: "grabbing", zIndex: 50 }}
      onDragStart={() => {
        dragging.current = true;
      }}
      onDragEnd={(_, info) => {
        // Spring back to origin, carrying the fling velocity as overshoot.
        animate(dragX, 0, {
          type: "spring",
          velocity: info.velocity.x,
          stiffness: 120,
          damping: 8,
        });
        animate(dragY, 0, {
          type: "spring",
          velocity: info.velocity.y,
          stiffness: 120,
          damping: 8,
        });
        setTimeout(() => {
          dragging.current = false;
        }, 0);
      }}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{
        opacity: isLit ? 1 : 0.5,
        scale: 1,
      }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
    >
      {/* 3D polyhedron + abbreviation overlay */}
      <motion.div
        role="button"
        tabIndex={0}
        onClick={() => {
          if (!dragging.current) onClick();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !dragging.current) onClick();
        }}
        aria-label={config.label}
        className="relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:rounded-full"
        whileHover={{ scale: 1.1 }}
        animate={{
          y: [0, -5, 0],
        }}
        transition={{
          y: { duration: floatDuration, delay: floatDelay, repeat: Infinity, ease: "easeInOut" },
        }}
        style={{ width: activeSize, height: activeSize, overflow: "visible" }}
      >
        {/* 3D Canvas */}
        <AgentPolyhedron
          shape={config.shape}
          color={config.color}
          status={status}
        />

        {/* Abbreviation overlay centered on top of the 3D scene */}
        <span
          className="pointer-events-none absolute inset-0 flex items-center justify-center font-bold select-none"
          style={{
            color: config.color,
            fontSize,
            textShadow: isDark
              ? `0 0 8px ${config.color}80`
              : `0 1px 3px rgba(0,0,0,0.25), 0 0 6px ${config.color}30`,
          }}
        >
          {config.abbr}
        </span>
      </motion.div>

      {/* Role label — below the circle */}
      <span
        className="absolute left-1/2 -translate-x-1/2 font-medium whitespace-nowrap transition-opacity duration-500"
        style={{
          top: "100%",
          marginTop: 6,
          color: isLit ? config.color : undefined,
          opacity: isLit ? 1 : 0.5,
          fontSize: labelSize,
        }}
      >
        {!isLit && (
          <span className="text-muted-foreground">{config.label}</span>
        )}
        {isLit && config.label}
      </span>
    </motion.div>
  );
}
