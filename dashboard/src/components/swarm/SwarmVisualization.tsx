/**
 * Main swarm visualization container.
 *
 * Measures its own size via ResizeObserver, computes radial positions,
 * renders the orbit ring (SVG), center detail text, agent nodes, and
 * handoff arcs.
 */

import { useRef, useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentActivity, Phase } from "@/lib/types";
import {
  ALL_AGENTS,
  getAgentConfig,
  getAgentPositions,
  getNodeSizes,
  PHASE_AGENTS,
  type AgentPosition,
} from "./swarm-constants";
import { AgentNode } from "./AgentNode";
import { HandoffArc, HandoffGlowFilter } from "./HandoffArc";

interface SwarmVisualizationProps {
  agents: AgentActivity[];
  phase?: Phase;
  activeHandoff: { from: string; to: string; id: string } | null;
  onAgentClick: (agent: AgentActivity) => void;
}

export function SwarmVisualization({
  agents,
  phase,
  activeHandoff,
  onAgentClick,
}: SwarmVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // Measure container
  useEffect(() => {
    if (!containerRef.current) return;
    let timeout: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver((entries) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        const { width, height } = entries[0].contentRect;
        setDimensions({ width, height });
      }, 100);
    });
    observer.observe(containerRef.current);
    return () => {
      observer.disconnect();
      clearTimeout(timeout);
    };
  }, []);

  // Which agents are part of the current phase's swarm (used for active styling)
  const phaseAgentNames = useMemo(
    () => (phase ? (PHASE_AGENTS[phase] ?? []) : []),
    [phase],
  );

  // All 7 agents are always positioned in the ring
  const positions = useMemo(
    () =>
      dimensions.width > 0
        ? getAgentPositions(ALL_AGENTS, dimensions.width, dimensions.height)
        : [],
    [dimensions.width, dimensions.height],
  );

  // Build a lookup: agent name → position
  const positionMap = useMemo(() => {
    const map = new Map<string, AgentPosition>();
    for (const p of positions) {
      map.set(p.name, p);
    }
    return map;
  }, [positions]);

  // Merge store agents with phase agents (some may not be in the store yet)
  const agentMap = useMemo(() => {
    const map = new Map<string, AgentActivity>();
    for (const a of agents) {
      map.set(a.agent_name, a);
    }
    return map;
  }, [agents]);

  // For each agent, merge store data with position. Agents outside the
  // current phase are always shown as idle.
  const resolvedAgents = useMemo(() => {
    const phaseSet = new Set(phaseAgentNames);
    const result: (AgentActivity & { pos: AgentPosition })[] = [];
    for (const pos of positions) {
      const storeAgent = agentMap.get(pos.name);
      const inPhase = phaseSet.has(pos.name);
      result.push({
        agent_name: pos.name,
        status: inPhase ? (storeAgent?.status ?? "idle") : "idle",
        phase: storeAgent?.phase ?? (phase ?? ""),
        detail: inPhase ? (storeAgent?.detail ?? "") : "",
        timestamp: storeAgent?.timestamp ?? 0,
        pos,
      });
    }
    return result;
  }, [positions, agentMap, phase, phaseAgentNames]);

  // Find the active agent with a detail message for the center display
  const activeDetail = useMemo(() => {
    const active = resolvedAgents.find(
      (a) => a.status === "active" && a.detail,
    );
    if (!active) return null;
    return { agentName: active.agent_name, detail: active.detail };
  }, [resolvedAgents]);

  const cx = dimensions.width / 2;
  const cy = dimensions.height / 2;
  const orbitRadius = Math.min(cx, cy) * 0.55;

  // Dynamic node sizes based on container dimensions
  const nodeSizes = useMemo(
    () => getNodeSizes(dimensions.width, dimensions.height),
    [dimensions.width, dimensions.height],
  );

  // Resolve handoff positions
  const handoffFrom = activeHandoff
    ? positionMap.get(activeHandoff.from)
    : undefined;
  const handoffTo = activeHandoff
    ? positionMap.get(activeHandoff.to)
    : undefined;

  // Config for the active agent (color for the center label)
  const activeConfig = activeDetail
    ? getAgentConfig(activeDetail.agentName)
    : null;

  return (
    <div ref={containerRef} className="relative h-full w-full overflow-hidden">
      {dimensions.width > 0 && (
        <>
          {/* SVG overlay: orbit ring + handoff arcs */}
          <svg className="pointer-events-none absolute inset-0 h-full w-full">
            <HandoffGlowFilter />

            {/* Orbit ring */}
            {orbitRadius > 0 && (
              <circle
                cx={cx}
                cy={cy}
                r={orbitRadius}
                fill="none"
                className="stroke-muted-foreground"
                strokeWidth={1.5}
                strokeDasharray="8 5"
                opacity={0.35}
              >
                <animateTransform
                  attributeName="transform"
                  type="rotate"
                  from={`0 ${cx} ${cy}`}
                  to={`360 ${cx} ${cy}`}
                  dur="60s"
                  repeatCount="indefinite"
                />
              </circle>
            )}

            {/* Handoff arc */}
            <AnimatePresence>
              {activeHandoff && handoffFrom && handoffTo && (
                <HandoffArc
                  key={activeHandoff.id}
                  from={handoffFrom}
                  to={handoffTo}
                  toName={activeHandoff.to}
                  centerX={cx}
                  centerY={cy}
                />
              )}
            </AnimatePresence>
          </svg>

          {/* Center: active agent's current work */}
          <div
            className="pointer-events-none absolute flex items-center justify-center"
            style={{
              left: cx,
              top: cy,
              transform: "translate(-50%, -50%)",
              width: orbitRadius * 1.3,
              height: orbitRadius * 1.3,
            }}
          >
            <AnimatePresence mode="wait">
              {activeDetail && activeConfig && (
                <motion.div
                  key={`${activeDetail.agentName}-${activeDetail.detail}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.4, ease: "easeInOut" }}
                  className="flex flex-col items-center gap-1.5 text-center"
                >
                  <span
                    className="text-xs font-semibold uppercase tracking-wider"
                    style={{ color: activeConfig.color }}
                  >
                    {activeConfig.label}
                  </span>
                  <span className="text-sm leading-relaxed text-muted-foreground">
                    {activeDetail.detail}
                  </span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Agent nodes */}
          <AnimatePresence>
            {resolvedAgents.map((agent) => (
              <AgentNode
                key={agent.agent_name}
                name={agent.agent_name}
                status={agent.status}
                x={agent.pos.x}
                y={agent.pos.y}
                nodeSizes={nodeSizes}
                onClick={() => onAgentClick(agent)}
              />
            ))}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
