"use client";

import {
  Background,
  BackgroundVariant,
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

const CLUSTER_RADIUS = 340;
const PAPER_RADIUS = 150;

type NodeData = {
  label: string;
  kind: "cluster" | "paper";
  isNew?: boolean;
};

// Cluster: heavy black-bordered box, serif label. The structural anchors.
function ClusterNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div className="max-w-[190px] border-2 border-black bg-white px-4 py-2.5 text-center">
      <Handle type="source" position={Position.Top} className="!border-0 !bg-black !opacity-0" />
      <Handle type="target" position={Position.Bottom} className="!border-0 !bg-black !opacity-0" />
      <span className="block font-display text-sm font-bold leading-tight text-black">
        {d.label}
      </span>
    </div>
  );
}

// Paper: hairline box. "New" papers invert to a black field (no color, per spec).
function PaperNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div
      className={`max-w-[150px] cursor-pointer border px-2.5 py-1.5 transition-colors duration-100 ${
        d.isNew ? "border-black bg-black text-white" : "border-black bg-white text-black hover:bg-black hover:text-white"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!border-0 !bg-black !opacity-0" />
      {d.isNew && (
        <span className="mb-0.5 block font-mono text-[8px] uppercase tracking-widest">New</span>
      )}
      <span className="block font-serif text-[11px] leading-tight line-clamp-3">{d.label}</span>
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
        position: { x: Math.cos(angle) * CLUSTER_RADIUS, y: Math.sin(angle) * CLUSTER_RADIUS },
        data: { label: c.label, kind: "cluster" } satisfies NodeData,
      });
    });

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
      animated: false,
      style: {
        stroke: "#000000",
        strokeWidth: e.type === "relationship" ? 2 : 1,
        strokeDasharray: e.type === "relationship" ? undefined : "4 4",
      },
    }));

    return { nodes, edges };
  }, [graph, latestVersion]);

  return (
    <div className="relative h-[640px] border-2 border-foreground bg-white">
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
        <Background variant={BackgroundVariant.Dots} color="#d4d4d4" gap={28} size={1} />
        <Controls />
      </ReactFlow>
      {selected && <PaperCard arxivId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
