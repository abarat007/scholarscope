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

// Editorial layout: each cluster is a titled block; its papers wrap into a
// multi-column grid beneath the header so the whole map stays landscape-shaped
// (matching the viewport) instead of two very tall columns. Membership is shown
// by grouping — only cross-cluster *relationships* are drawn, arcing over the
// header row where the actual map of the field lives.
const NODE_W = 260;
const PAPER_H = 80;
const ROW_H = 96;
const SUBCOL_GAP = 24;
const CLUSTER_GAP = 96;
const HEADER_OFFSET = 150;
const ROWS_PER_SUBCOL = 7;

type NodeData = {
  label: string;
  kind: "cluster" | "paper";
  index?: number;
  isNew?: boolean;
};

function ClusterNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div className="border-2 border-black bg-white px-4 py-3" style={{ width: NODE_W }}>
      {/* both handles sit at top; relationship edges arc above the row */}
      <Handle id="s" type="source" position={Position.Top} className="!border-0 !bg-black !opacity-0" />
      <Handle id="t" type="target" position={Position.Top} className="!border-0 !bg-black !opacity-0" />
      <span className="mb-1 block font-mono text-[10px] uppercase tracking-widest text-secondary">
        Cluster {String((d.index ?? 0) + 1).padStart(2, "0")}
      </span>
      <span className="block font-display text-base font-bold leading-tight text-black">
        {d.label}
      </span>
    </div>
  );
}

function PaperNode({ data }: NodeProps) {
  const d = data as NodeData;
  return (
    <div
      className={`flex cursor-pointer flex-col justify-center overflow-hidden border px-3 py-2 transition-colors duration-100 ${
        d.isNew
          ? "border-black bg-black text-white"
          : "border-black bg-white text-black hover:bg-black hover:text-white"
      }`}
      style={{ width: NODE_W, height: PAPER_H }}
    >
      {d.isNew && (
        <span className="mb-0.5 block font-mono text-[8px] uppercase tracking-widest">New</span>
      )}
      <span className="line-clamp-3 font-serif text-[12px] leading-snug">{d.label}</span>
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

    const papersByCluster = new Map<number, typeof graph.nodes>();
    for (const n of graph.nodes) {
      if (n.type !== "paper" || n.cluster_id === null) continue;
      const arr = papersByCluster.get(n.cluster_id) ?? [];
      arr.push(n);
      papersByCluster.set(n.cluster_id, arr);
    }

    const nodes: Node[] = [];
    let cursorX = 0;

    clusters.forEach((c, ci) => {
      const idNum = Number(c.id.split(":")[1]);
      const papers = papersByCluster.get(idNum) ?? [];
      const subCols = Math.max(1, Math.ceil(papers.length / ROWS_PER_SUBCOL));
      const rows = Math.max(1, Math.ceil(papers.length / subCols));
      const blockWidth = subCols * NODE_W + (subCols - 1) * SUBCOL_GAP;

      // Header centered over its block of sub-columns.
      nodes.push({
        id: c.id,
        type: "cluster",
        position: { x: cursorX + (blockWidth - NODE_W) / 2, y: 0 },
        data: { label: c.label, kind: "cluster", index: ci } satisfies NodeData,
        draggable: false,
      });

      // Fill column-major so reading order runs top-to-bottom, then rightward.
      papers.forEach((p, j) => {
        const subCol = Math.floor(j / rows);
        const row = j % rows;
        nodes.push({
          id: p.id,
          type: "paper",
          position: {
            x: cursorX + subCol * (NODE_W + SUBCOL_GAP),
            y: HEADER_OFFSET + row * ROW_H,
          },
          data: {
            label: p.label,
            kind: "paper",
            isNew: p.added_in_version === latestVersion && latestVersion > 1,
          } satisfies NodeData,
          draggable: false,
        });
      });

      cursorX += blockWidth + CLUSTER_GAP;
    });

    // Only cross-cluster relationships — the membership web is gone.
    const edges: Edge[] = graph.edges
      .filter((e) => e.type === "relationship")
      .map((e, i) => ({
        id: `r${i}`,
        source: e.source,
        target: e.target,
        sourceHandle: "s",
        targetHandle: "t",
        label: e.label ?? undefined,
        type: "default",
        style: { stroke: "#000000", strokeWidth: 2 },
      }));

    return { nodes, edges };
  }, [graph, latestVersion]);

  return (
    <div className="relative h-[680px] border-2 border-foreground bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.18 }}
        minZoom={0.15}
        nodesConnectable={false}
        proOptions={{ hideAttribution: true }}
        onNodeClick={(_, node) => {
          if (node.type === "paper") setSelected(node.id);
        }}
      >
        <Background variant={BackgroundVariant.Dots} color="#d4d4d4" gap={28} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
      {selected && <PaperCard arxivId={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
