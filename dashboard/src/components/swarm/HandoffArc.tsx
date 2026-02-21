/**
 * Animated SVG arc showing a handoff between two agents.
 *
 * Draws a curved path from source to destination with a glow effect,
 * then fades out gracefully.
 */

import { motion } from "framer-motion";
import { getAgentConfig } from "./swarm-constants";
import type { AgentPosition } from "./swarm-constants";

interface HandoffArcProps {
  from: AgentPosition;
  to: AgentPosition;
  /** Name of the destination agent (used for glow color). */
  toName: string;
  /** Center of the radial layout (arc curves inward toward this point). */
  centerX: number;
  centerY: number;
}

/**
 * Build a quadratic bezier curve between two points.
 * The control point is offset toward the center for a nice arc.
 */
function arcPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  cx: number,
  cy: number,
): string {
  // Pull control point toward center for a gentle inward curve
  const cpx = (x1 + x2) / 2 + (cx - (x1 + x2) / 2) * 0.4;
  const cpy = (y1 + y2) / 2 + (cy - (y1 + y2) / 2) * 0.4;
  return `M ${x1} ${y1} Q ${cpx} ${cpy} ${x2} ${y2}`;
}

export function HandoffArc({ from, to, toName, centerX, centerY }: HandoffArcProps) {
  const config = getAgentConfig(toName);
  const d = arcPath(from.x, from.y, to.x, to.y, centerX, centerY);

  return (
    <motion.path
      d={d}
      fill="none"
      stroke={config.color}
      strokeWidth={3}
      strokeLinecap="round"
      filter="url(#handoff-glow)"
      initial={{ pathLength: 0, opacity: 1 }}
      animate={{ pathLength: 1, opacity: [1, 1, 0] }}
      transition={{
        pathLength: { duration: 0.6, ease: "easeOut" },
        opacity: { duration: 0.8, times: [0, 0.7, 1], ease: "easeIn" },
      }}
    />
  );
}

/** SVG filter definition for the glow effect. Place inside an <svg> defs. */
export function HandoffGlowFilter() {
  return (
    <defs>
      <filter id="handoff-glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="4" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
  );
}
