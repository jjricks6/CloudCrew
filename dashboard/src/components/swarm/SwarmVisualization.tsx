/**
 * Main swarm visualization container.
 *
 * Measures its own size via ResizeObserver, computes radial positions,
 * renders the orbit ring (SVG), center hub, agent nodes, and handoff arcs.
 */

import { useRef, useState, useEffect, useMemo } from "react";
import { AnimatePresence } from "framer-motion";
import type { AgentActivity, Phase, PhaseStatus } from "@/lib/types";
import {
  getAgentPositions,
  PHASE_AGENTS,
  type AgentPosition,
} from "./swarm-constants";
import { AgentNode } from "./AgentNode";
import { CenterHub } from "./CenterHub";
import { HandoffArc, HandoffGlowFilter } from "./HandoffArc";

interface SwarmVisualizationProps {
  agents: AgentActivity[];
  phase?: Phase;
  phaseStatus?: PhaseStatus;
  activeHandoff: { from: string; to: string; id: string } | null;
  onAgentClick: (agent: AgentActivity) => void;
}

export function SwarmVisualization({
  agents,
  phase,
  phaseStatus,
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

  // Determine which agents belong in the current phase's swarm
  const phaseAgentNames = useMemo(
    () => (phase ? (PHASE_AGENTS[phase] ?? []) : []),
    [phase],
  );

  // Compute positions only for agents that should be in the ring
  const positions = useMemo(
    () =>
      dimensions.width > 0 && phaseAgentNames.length > 0
        ? getAgentPositions(
            phaseAgentNames,
            dimensions.width,
            dimensions.height,
          )
        : [],
    [phaseAgentNames, dimensions.width, dimensions.height],
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

  // For each expected phase agent, get or create a stub
  const resolvedAgents = useMemo(() => {
    const result: (AgentActivity & { pos: AgentPosition })[] = [];
    for (const pos of positions) {
      const storeAgent = agentMap.get(pos.name);
      result.push({
        agent_name: pos.name,
        status: storeAgent?.status ?? "idle",
        phase: storeAgent?.phase ?? (phase ?? ""),
        detail: storeAgent?.detail ?? "",
        timestamp: storeAgent?.timestamp ?? 0,
        pos,
      });
    }
    return result;
  }, [positions, agentMap, phase]);

  const cx = dimensions.width / 2;
  const cy = dimensions.height / 2;
  const orbitRadius = Math.min(cx, cy) * 0.55;

  // Resolve handoff positions
  const handoffFrom = activeHandoff
    ? positionMap.get(activeHandoff.from)
    : undefined;
  const handoffTo = activeHandoff
    ? positionMap.get(activeHandoff.to)
    : undefined;

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
                className="stroke-border"
                strokeWidth={1}
                strokeDasharray="6 4"
                opacity={0.5}
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

          {/* Center hub */}
          <CenterHub
            phase={phase}
            phaseStatus={phaseStatus}
            cx={cx}
            cy={cy}
          />

          {/* Agent nodes */}
          <AnimatePresence>
            {resolvedAgents.map((agent) => (
              <AgentNode
                key={agent.agent_name}
                name={agent.agent_name}
                status={agent.status}
                detail={agent.detail}
                x={agent.pos.x}
                y={agent.pos.y}
                bubbleSide={agent.pos.x >= cx ? "right" : "left"}
                onClick={() => onAgentClick(agent)}
              />
            ))}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
