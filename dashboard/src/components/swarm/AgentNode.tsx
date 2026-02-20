/**
 * Animated agent circle for the swarm visualization.
 *
 * - Active: pulsing glow, full opacity, thought bubble with current task
 * - Idle: muted, smaller, no bubble
 * - Smooth transitions between states (0.5s)
 */

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  getAgentConfig,
  NODE_SIZE_ACTIVE,
  NODE_SIZE_IDLE,
} from "./swarm-constants";

interface AgentNodeProps {
  name: string;
  status: "active" | "idle";
  detail: string;
  x: number;
  y: number;
  /** Which side to place the thought bubble on. */
  bubbleSide: "left" | "right";
  onClick: () => void;
}

function ThoughtBubble({
  detail,
  side,
}: {
  detail: string;
  side: "left" | "right";
}) {
  const truncated =
    detail.length > 60 ? detail.slice(0, 57) + "..." : detail;

  const isRight = side === "right";

  return (
    <motion.div
      initial={{ opacity: 0, x: isRight ? -6 : 6 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: isRight ? -6 : 6 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`absolute top-1/2 -translate-y-1/2 ${
        isRight ? "left-full ml-3" : "right-full mr-3"
      }`}
    >
      <div className="relative w-[240px] rounded-lg border bg-card px-3 py-1.5 text-xs text-card-foreground shadow-md">
        <p className="leading-relaxed">{truncated}</p>
        {/* Triangle tail pointing toward the agent circle */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 ${
            isRight ? "right-full" : "left-full"
          }`}
        >
          {isRight ? (
            <>
              <div className="h-0 w-0 border-y-[6px] border-r-[6px] border-y-transparent border-r-border" />
              <div className="-ml-[1px] -mt-[12px] h-0 w-0 border-y-[6px] border-r-[6px] border-y-transparent border-r-card" />
            </>
          ) : (
            <>
              <div className="h-0 w-0 border-y-[6px] border-l-[6px] border-y-transparent border-l-border" />
              <div className="-mr-[1px] -mt-[12px] h-0 w-0 border-y-[6px] border-l-[6px] border-y-transparent border-l-card" />
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function AgentNode({
  name,
  status,
  detail,
  x,
  y,
  bubbleSide,
  onClick,
}: AgentNodeProps) {
  const config = getAgentConfig(name);
  const isActive = status === "active";
  const size = isActive ? NODE_SIZE_ACTIVE : NODE_SIZE_IDLE;

  // Delay bubble appearance by 1s when transitioning idle → active.
  // When going idle, keep bubble visible for 4s so "Finished" messages are readable.
  const [showBubble, setShowBubble] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    clearTimeout(timerRef.current);
    if (isActive) {
      timerRef.current = setTimeout(() => setShowBubble(true), 1000);
    } else {
      // Keep bubble visible for 4s after going idle so the user can read the message
      timerRef.current = setTimeout(() => setShowBubble(false), 4000);
    }
    return () => {
      clearTimeout(timerRef.current);
    };
  }, [isActive]);

  return (
    <motion.div
      layout
      className="absolute flex items-center"
      style={{ left: x, top: y }}
      initial={{ opacity: 0, scale: 0.8, x: "-50%", y: "-50%" }}
      animate={{
        x: "-50%",
        y: "-50%",
        opacity: isActive ? 1 : 0.5,
        scale: 1,
      }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ type: "spring", stiffness: 200, damping: 25 }}
    >
      <div className="flex flex-col items-center">
        {/* Agent circle */}
        <motion.button
          type="button"
          onClick={onClick}
          aria-label={config.label}
          className="relative flex items-center justify-center rounded-full border-[3px] bg-card transition-colors hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          style={{ borderColor: config.color }}
          animate={{
            width: size,
            height: size,
            boxShadow: isActive
              ? [
                  `0 0 12px 2px ${config.color}60`,
                  `0 0 24px 6px ${config.color}40`,
                  `0 0 12px 2px ${config.color}60`,
                ]
              : `0 0 0px 0px ${config.color}00`,
            scale: isActive ? [1, 1.06, 1] : 1,
          }}
          transition={
            isActive
              ? {
                  boxShadow: { duration: 2, repeat: Infinity, ease: "easeInOut" },
                  scale: { duration: 2, repeat: Infinity, ease: "easeInOut" },
                  width: { duration: 0.5 },
                  height: { duration: 0.5 },
                }
              : { duration: 0.5, ease: "easeOut" }
          }
        >
          <span
            className="text-sm font-bold select-none"
            style={{ color: config.color }}
          >
            {config.abbr}
          </span>
        </motion.button>

        {/* Role label */}
        <span
          className="mt-1.5 text-[10px] font-medium whitespace-nowrap transition-opacity duration-500"
          style={{
            color: isActive ? config.color : undefined,
            opacity: isActive ? 1 : 0.5,
          }}
        >
          {!isActive && (
            <span className="text-muted-foreground">{config.label}</span>
          )}
          {isActive && config.label}
        </span>
      </div>

      {/* Thought bubble (to the side, delayed after activation) */}
      <AnimatePresence mode="wait">
        {showBubble && detail && (
          <ThoughtBubble
            key={`bubble-${name}`}
            detail={detail}
            side={bubbleSide}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
