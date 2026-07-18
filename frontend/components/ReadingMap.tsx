"use client";

import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo, useState } from "react";
import type { LandscapeGraph } from "@/lib/api";
import PaperCard from "./PaperCard";

// Deterministic radial layout: clusters on an inner ring, their papers fanned
// around each cluster. Keeps the graph readable without a physics engine.
const CLUSTER_RADIUS = 340;
const PAPER_RADIUS = 150;

type NodeData = {
  label: string;
  kind: "cluster" | "paper";
  isNew?: boolean;
};

function ClusterNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div className="rounded-xl border-2 border-accent bg-accent/15 px-4 py-2.5 text-center shadow-lg max-w-[180px]">
      <Handle type="source" position={Position.Top} className="!opacity-0" />
      <Handle type="target" position={Position.Bottom} className="!opacity-0" />
      <span className="text-sm font-semibold text-accent-soft leading-tight">{d.label}</span>
    </div>
  );
}

function PaperNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div
      className={`rounded-lg border bg-ink-800/90 px-2.5 py-1.5 max-w-[150px] cursor-pointer hover:border-accent transition-colors ${
        d.isNew ? "border-emerald-500/70" : "border-ink-600"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!opacity-0" />
      {d.isNew && (
        <span className="block text-[9px] uppercase tracking-wide text-emerald-400 mb-0.5">new</span>
      )}
      <span className="text-[11px] text-slate-300 leading-tight line-clamp-3 block">{d.label}</span>
    </div>
  );
}

const nodeTypes = { cluster: ClusterNode, paper: PaperNode };

export default function ReadingMap({
  graph,
  latestVersion,
}: {
  graph: LandscapeGraph;
  latestVersion: number;
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    const clusters = graph.nodes.filter((n) => n.type === "cluster");
    const clusterAngle = new Map<string, number>();
    const nodes: Node[] = [];

    clusters.forEach((c, ci) => {
      const angle = (2 * Math.PI * ci) / Math.max(clusters.length, 1);
      clusterAngle.set(c.id, angle);
      nodes.push({
        id: c.id,
        type: "cluster",
        position: {
          x: Math.cos(angle) * CLUSTER_RADIUS,
          y: Math.sin(angle) * CLUSTER_RADIUS,
        },
        data: { label: c.label, kind: "cluster" } satisfies NodeData,
      });
    });

    // group papers by their cluster to fan them out locally
    const papersByCluster = new Map<number, string[]>();
    for (const n of graph.nodes) {
      if (n.type === "paper" && n.cluster_id !== null) {
        const arr = papersByCluster.get(n.cluster_id) ?? [];
        arr.push(n.id);
        papersByCluster.set(n.cluster_id, arr);
      }
    }

    for (const n of graph.nodes) {
      if (n.type !== "paper" || n.cluster_id === null) continue;
      const clusterKey = `cluster:${n.cluster_id}`;
      const base = clusterAngle.get(clusterKey) ?? 0;
      const siblings = papersByCluster.get(n.cluster_id) ?? [];
      const idx = siblings.indexOf(n.id);
      const spread = ((idx - (siblings.length - 1) / 2) * 0.5) / Math.max(siblings.length, 1);
      const pa = base + spread * Math.PI;
      nodes.push({
        id: n.id,
        type: "paper",
        position: {
          x: Math.cos(base) * CLUSTER_RADIUS + Math.cos(pa) * PAPER_RADIUS * (1 + idx * 0.15),
          y: Math.sin(base) * CLUSTER_RADIUS + Math.sin(pa) * PAPER_RADIUS * (1 + idx * 0.15),
        },
        data: {
          label: n.label,
          kind: "paper",
          isNew: n.added_in_version === latestVersion && latestVersion > 1,
        } satisfies NodeData,
      });
    }

    const edges: Edge[] = graph.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.type === "relationship" ? e.label ?? undefined : undefined,
      animated: e.type === "relationship",
      style: {
        stroke: e.type === "relationship" ? "#7c9cff" : "#3a3a4d",
        strokeWidth: e.type === "relationship" ? 2 : 1,
      },
      labelStyle: { fill: "#a5b8ff", fontSize: 10 },
      labelBgStyle: { fill: "#12121a" },
    }));

    return { nodes, edges };
  }, [graph, latestVersion]);

  return (
    <div className="relative h-[640px] rounded-xl border border-ink-800 bg-ink-950 overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => {
          if (node.type === "paper") setSelected(node.id);
        }}
      >
        <Background color="#282836" gap={24} />
        <Controls className="!bg-ink-800 !border-ink-700" />
      </ReactFlow>
      {selected && <PaperCard arxivId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
