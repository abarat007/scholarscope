"use client";

const KEY = "scholarscope:topics";

export interface TopicVisit {
  topic: string;
  lastPaperCount: number;
  visitedAt: number;
}

export function loadHistory(): TopicVisit[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "[]") as TopicVisit[];
  } catch {
    return [];
  }
}

export function recordVisit(topic: string, paperCount: number): TopicVisit[] {
  const history = loadHistory().filter((v) => v.topic !== topic);
  const updated = [{ topic, lastPaperCount: paperCount, visitedAt: Date.now() }, ...history];
  localStorage.setItem(KEY, JSON.stringify(updated.slice(0, 30)));
  return updated;
}

export function priorPaperCount(topic: string): number | null {
  const visit = loadHistory().find((v) => v.topic === topic);
  return visit ? visit.lastPaperCount : null;
}
