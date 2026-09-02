"use client";

import { useEffect, useRef } from "react";

type NodeKind = "tiny" | "normal" | "hub";

type NetworkNode = {
  id: number;
  cluster: number;
  kind: NodeKind;
  radius: number;
  baseX: number;
  baseY: number;
  phaseX: number;
  phaseY: number;
  amplitudeX: number;
  amplitudeY: number;
  speedX: number;
  speedY: number;
  label: string;
  x: number;
  y: number;
  pointerOffsetX: number;
  pointerOffsetY: number;
  inspection: number;
  neighbors: number[];
};

type NetworkEdge = {
  from: number;
  to: number;
  importance: number;
  kind: "local" | "bridge" | "hub";
  phase: number;
  breathSpeed: number;
};

type KnowledgeGraph = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
};

type PointerState = {
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  inside: boolean;
  hoveredId: number | null;
};

type TraceState = {
  path: number[];
  startedAt: number;
  stepDuration: number;
  holdDuration: number;
  fadeDuration: number;
  color: "ink" | "rust";
  mode: "autonomous" | "user";
};

const LABELS = ["SOURCE", "CHUNK", "ENTITY", "RELATION", "EVIDENCE"];

const CLUSTERS = [
  { x: 0.48, y: 0.48, width: 0.2, height: 0.24 },
  { x: 0.28, y: 0.29, width: 0.17, height: 0.16 },
  { x: 0.68, y: 0.27, width: 0.17, height: 0.16 },
  { x: 0.75, y: 0.56, width: 0.2, height: 0.2 },
  { x: 0.46, y: 0.73, width: 0.21, height: 0.17 },
  { x: 0.16, y: 0.62, width: 0.13, height: 0.16 },
  { x: 0.89, y: 0.75, width: 0.08, height: 0.11 },
] as const;

function createRandom(seed: number) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let result = value;
    result = Math.imul(result ^ (result >>> 15), result | 1);
    result ^= result + Math.imul(result ^ (result >>> 7), result | 61);
    return ((result ^ (result >>> 14)) >>> 0) / 4294967296;
  };
}

function nodeCountForViewport(viewportWidth: number) {
  if (viewportWidth <= 640) {
    return 56;
  }
  if (viewportWidth <= 850) {
    return 112;
  }
  if (viewportWidth <= 1100) {
    return 168;
  }
  return 288;
}

function graphForViewport(viewportWidth: number): KnowledgeGraph {
  const nodeCount = nodeCountForViewport(viewportWidth);
  const clusterCount = viewportWidth <= 640 ? 4 : viewportWidth <= 850 ? 5 : viewportWidth <= 1100 ? 6 : 7;
  const random = createRandom(0x74726163 + nodeCount * 97);
  const nodes: NetworkNode[] = [];
  const clusters: number[][] = Array.from({ length: clusterCount }, () => []);
  const hubs: number[][] = Array.from({ length: clusterCount }, () => []);

  for (let clusterIndex = 0; clusterIndex < clusterCount; clusterIndex += 1) {
    const cluster = CLUSTERS[clusterIndex];
    const size = Math.floor(nodeCount / clusterCount) + (clusterIndex < nodeCount % clusterCount ? 1 : 0);
    const hubCount = Math.max(1, Math.round(size * 0.08));
    const normalCount = hubCount + Math.max(1, Math.round(size * 0.22));

    for (let localIndex = 0; localIndex < size; localIndex += 1) {
      const kind: NodeKind = localIndex < hubCount ? "hub" : localIndex < normalCount ? "normal" : "tiny";
      const angle = random() * Math.PI * 2;
      const distance = Math.pow(random(), kind === "hub" ? 1.85 : kind === "normal" ? 1.16 : 0.66);
      const satellite = kind === "tiny" && random() > 0.92 ? 1.72 : 1;
      const radius = kind === "hub" ? 4 + random() * 3 : kind === "normal" ? 2 + random() : 1 + random() * 0.8;
      const drift = kind === "hub" ? 1 + random() * 3 : kind === "normal" ? 2 + random() * 4 : 3 + random() * 7;
      const node: NetworkNode = {
        id: nodes.length,
        cluster: clusterIndex,
        kind,
        radius,
        baseX: Math.min(0.98, Math.max(0.02, cluster.x + Math.cos(angle) * cluster.width * distance * satellite)),
        baseY: Math.min(0.96, Math.max(0.04, cluster.y + Math.sin(angle) * cluster.height * distance * satellite)),
        phaseX: random() * Math.PI * 2,
        phaseY: random() * Math.PI * 2,
        amplitudeX: drift * (0.72 + random() * 0.45),
        amplitudeY: drift * (0.72 + random() * 0.45),
        speedX: 0.45 + random() * 0.45,
        speedY: 0.4 + random() * 0.5,
        label: LABELS[(nodes.length + clusterIndex) % LABELS.length],
        x: 0,
        y: 0,
        pointerOffsetX: 0,
        pointerOffsetY: 0,
        inspection: 0,
        neighbors: [],
      };
      nodes.push(node);
      clusters[clusterIndex].push(node.id);
      if (kind === "hub") {
        hubs[clusterIndex].push(node.id);
      }
    }
  }

  const edges: NetworkEdge[] = [];
  const edgeKeys = new Set<string>();
  const connect = (first: number, second: number, importance: number, kind: NetworkEdge["kind"]) => {
    if (first === second) {
      return false;
    }
    const from = Math.min(first, second);
    const to = Math.max(first, second);
    const key = `${from}:${to}`;
    if (edgeKeys.has(key)) {
      return false;
    }
    edgeKeys.add(key);
    edges.push({ from, to, importance, kind, phase: random() * Math.PI * 2, breathSpeed: 0.38 + random() * 0.5 });
    nodes[from].neighbors.push(to);
    nodes[to].neighbors.push(from);
    return true;
  };

  clusters.forEach((clusterNodes, clusterIndex) => {
    const clusterHubs = hubs[clusterIndex];
    clusterNodes.forEach((nodeId) => {
      if (!clusterHubs.includes(nodeId)) {
        connect(nodeId, clusterHubs[Math.floor(random() * clusterHubs.length)], 0.09 + random() * 0.04, "local");
      }
    });
    for (let index = 1; index < clusterHubs.length; index += 1) {
      connect(clusterHubs[index - 1], clusterHubs[index], 0.18 + random() * 0.04, "hub");
    }
  });

  for (let clusterIndex = 0; clusterIndex < clusterCount; clusterIndex += 1) {
    const nextCluster = (clusterIndex + 1) % clusterCount;
    connect(
      hubs[clusterIndex][Math.floor(random() * hubs[clusterIndex].length)],
      hubs[nextCluster][Math.floor(random() * hubs[nextCluster].length)],
      0.16 + random() * 0.05,
      "bridge",
    );
  }
  for (let bridge = 0; bridge < clusterCount + 3; bridge += 1) {
    const firstCluster = Math.floor(random() * clusterCount);
    let secondCluster = Math.floor(random() * clusterCount);
    if (secondCluster === firstCluster) {
      secondCluster = (secondCluster + 2) % clusterCount;
    }
    const first = clusters[firstCluster][Math.floor(random() * clusters[firstCluster].length)];
    const second = hubs[secondCluster][Math.floor(random() * hubs[secondCluster].length)];
    connect(first, second, 0.12 + random() * 0.08, "bridge");
  }

  const targetEdges = Math.round(nodeCount * (nodeCount > 200 ? 1.9 : nodeCount > 130 ? 1.72 : nodeCount > 80 ? 1.58 : 1.42));
  let attempts = 0;
  while (edges.length < targetEdges && attempts < targetEdges * 18) {
    const clusterIndex = Math.floor(random() * clusterCount);
    const clusterNodes = clusters[clusterIndex];
    const first = clusterNodes[Math.floor(random() * clusterNodes.length)];
    const second = clusterNodes[Math.floor(random() * clusterNodes.length)];
    connect(first, second, 0.04 + random() * 0.07, "local");
    attempts += 1;
  }

  return { nodes, edges };
}

function easeInOut(value: number) {
  return value < 0.5 ? 2 * value * value : 1 - Math.pow(-2 * value + 2, 2) / 2;
}

function distance(firstX: number, firstY: number, secondX: number, secondY: number) {
  return Math.hypot(firstX - secondX, firstY - secondY);
}

export function HeroKnowledgeNetwork() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    const graphRef: { current: KnowledgeGraph } = { current: graphForViewport(window.innerWidth) };
    const pointer: PointerState = { x: 0, y: 0, targetX: 0, targetY: 0, inside: false, hoveredId: null };
    const traceRef: { current: TraceState | null } = { current: null };
    const neighborhood = new Set<number>();
    const autonomousRandom = createRandom(0x5345434f4e44);
    const size = { width: 0, height: 0, dpr: 1 };
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frameId: number | null = null;
    let traceTimeout: number | null = null;
    let inView = true;
    let nextAutonomousTraceAt = performance.now() + 2600 + autonomousRandom() * 2400;
    let labelNodeId: number | null = null;
    let labelOpacity = 0;
    let pausedAt: number | null = null;

    const updateNodePositions = (time: number) => {
      graphRef.current.nodes.forEach((node) => {
        const idleX = reduceMotion ? 0 : time * 0.00018 * node.speedX;
        const idleY = reduceMotion ? 0 : time * 0.00016 * node.speedY;
        const baseX = node.baseX * size.width;
        const baseY = node.baseY * size.height;
        const x = baseX + Math.cos(idleX + node.phaseX) * node.amplitudeX + Math.sin(idleX * 0.61 + node.phaseY) * node.amplitudeX * 0.28;
        const y = baseY + Math.sin(idleY + node.phaseY) * node.amplitudeY + Math.cos(idleY * 0.58 + node.phaseX) * node.amplitudeY * 0.26;
        let targetOffsetX = 0;
        let targetOffsetY = 0;
        let targetInspection = 0;

        if (pointer.inside) {
          const nodeDistance = distance(x, y, pointer.x, pointer.y);
          if (nodeDistance < 112) {
            const influence = 1 - nodeDistance / 112;
            const maximumShift = node.kind === "hub" ? 2.5 : node.kind === "normal" ? 3.5 : 5;
            targetOffsetX = ((x - pointer.x) / Math.max(nodeDistance, 1)) * influence * maximumShift;
            targetOffsetY = ((y - pointer.y) / Math.max(nodeDistance, 1)) * influence * maximumShift;
            targetInspection = influence;
          }
        }
        node.pointerOffsetX += (targetOffsetX - node.pointerOffsetX) * 0.1;
        node.pointerOffsetY += (targetOffsetY - node.pointerOffsetY) * 0.1;
        node.inspection += (targetInspection - node.inspection) * 0.12;
        node.x = x + node.pointerOffsetX;
        node.y = y + node.pointerOffsetY;
      });
    };

    const findHoveredNode = () => {
      if (!pointer.inside) {
        pointer.hoveredId = null;
        return;
      }
      let closest: NetworkNode | null = null;
      let closestDistance = 62;
      for (const node of graphRef.current.nodes) {
        const nodeDistance = distance(node.x, node.y, pointer.x, pointer.y);
        if (nodeDistance < closestDistance) {
          closest = node;
          closestDistance = nodeDistance;
        }
      }
      pointer.hoveredId = closest === null ? null : closest.id;
    };

    const draw = (time: number) => {
      if (size.width === 0 || size.height === 0) {
        return;
      }
      pointer.x += (pointer.targetX - pointer.x) * 0.18;
      pointer.y += (pointer.targetY - pointer.y) * 0.18;
      updateNodePositions(time);
      findHoveredNode();

      context.clearRect(0, 0, size.width, size.height);
      const graph = graphRef.current;
      const activeTrace = traceRef.current;
      neighborhood.clear();
      if (pointer.hoveredId !== null) {
        neighborhood.add(pointer.hoveredId);
        graph.nodes[pointer.hoveredId].neighbors.forEach((neighbor) => neighborhood.add(neighbor));
      }

      graph.edges.forEach((edge) => {
        const isLocal = neighborhood.has(edge.from) && neighborhood.has(edge.to);
        const breathing = 0.9 + Math.sin(time * 0.00026 * edge.breathSpeed + edge.phase) * 0.1;
        const alpha = (pointer.hoveredId === null ? edge.importance : isLocal ? Math.max(0.24, edge.importance * 1.8) : edge.importance * 0.52) * breathing;
        context.beginPath();
        context.moveTo(graph.nodes[edge.from].x, graph.nodes[edge.from].y);
        context.lineTo(graph.nodes[edge.to].x, graph.nodes[edge.to].y);
        context.strokeStyle = `rgba(17, 17, 17, ${alpha})`;
        context.lineWidth = isLocal ? 0.76 : edge.kind === "hub" ? 0.62 : 0.46;
        context.stroke();
      });

      let traceFade = 1;
      if (activeTrace) {
        const elapsed = time - activeTrace.startedAt;
        const propagation = (activeTrace.path.length - 1) * activeTrace.stepDuration;
        const fadeStart = propagation + activeTrace.holdDuration;
        if (!reduceMotion && elapsed > fadeStart) {
          traceFade = Math.max(0, 1 - (elapsed - fadeStart) / activeTrace.fadeDuration);
        }

        activeTrace.path.slice(0, -1).forEach((nodeId, index) => {
          const nextNodeId = activeTrace.path[index + 1];
          const edgeStart = index * activeTrace.stepDuration;
          const progress = reduceMotion ? 1 : Math.min(1, Math.max(0, (elapsed - edgeStart) / activeTrace.stepDuration));
          if (progress <= 0) {
            return;
          }
          const from = graph.nodes[nodeId];
          const to = graph.nodes[nextNodeId];
          const eased = easeInOut(progress);
          context.beginPath();
          context.moveTo(from.x, from.y);
          context.lineTo(from.x + (to.x - from.x) * eased, from.y + (to.y - from.y) * eased);
          context.strokeStyle = activeTrace.color === "rust" ? `rgba(228, 91, 50, ${0.76 * traceFade})` : `rgba(17, 17, 17, ${0.82 * traceFade})`;
          context.lineWidth = 1.15;
          context.stroke();
        });

        if (!reduceMotion && elapsed > fadeStart + activeTrace.fadeDuration) {
          traceRef.current = null;
          if (activeTrace.mode === "user") {
            nextAutonomousTraceAt = time + 2500 + autonomousRandom() * 2500;
          }
        }
      }

      graph.nodes.forEach((node) => {
        const isHovered = node.id === pointer.hoveredId;
        const isNeighbor = neighborhood.has(node.id);
        const traceIndex = activeTrace?.path.indexOf(node.id) ?? -1;
        let pulse = 0;
        if (traceIndex >= 0 && activeTrace) {
          const reached = time - activeTrace.startedAt - traceIndex * activeTrace.stepDuration;
          if (reached >= 0 && reached < 340) {
            pulse = Math.sin((reached / 340) * Math.PI) * 0.27 * traceFade;
          }
        }
        const focalStrength = isHovered ? 1 : node.inspection;
        const scale = 1 + focalStrength * 0.34 + (isNeighbor ? 0.1 : 0) + pulse;
        const idleAlpha = node.kind === "tiny" ? 0.42 : node.kind === "normal" ? 0.68 : 0.84;
        const alpha = traceIndex >= 0 ? 0.94 : Math.min(0.95, idleAlpha + focalStrength * 0.28 + (isNeighbor ? 0.08 : 0));
        context.beginPath();
        context.arc(node.x, node.y, node.radius * scale, 0, Math.PI * 2);
        context.fillStyle = `rgba(17, 17, 17, ${alpha})`;
        context.fill();
      });

      if (pointer.inside) {
        context.beginPath();
        context.arc(pointer.x, pointer.y, 8, 0, Math.PI * 2);
        context.strokeStyle = "rgba(17, 17, 17, 0.34)";
        context.lineWidth = 0.6;
        context.stroke();
      }

      if (pointer.hoveredId !== null) {
        labelNodeId = pointer.hoveredId;
      }
      labelOpacity += ((pointer.hoveredId === null ? 0 : 1) - labelOpacity) * 0.12;
      if (labelNodeId !== null && labelOpacity > 0.02) {
        const labeledNode = graph.nodes[labelNodeId];
        context.fillStyle = `rgba(17, 17, 17, ${0.78 * labelOpacity})`;
        context.font = "9px var(--font-geist-mono), monospace";
        context.fillText(labeledNode.label, labeledNode.x + 10, labeledNode.y - 9);
      }
      if (pointer.hoveredId === null && labelOpacity <= 0.02) {
        labelNodeId = null;
      }
    };

    const scheduleFrame = () => {
      if (reduceMotion || !inView || document.visibilityState !== "visible" || frameId !== null) {
        return;
      }
      frameId = window.requestAnimationFrame((time) => {
        frameId = null;
        if (traceRef.current === null && time >= nextAutonomousTraceAt) {
          const graph = graphRef.current;
          const startNode = graph.nodes[Math.floor(autonomousRandom() * graph.nodes.length)];
          traceFrom(startNode.id, "autonomous", time);
        } else {
          draw(time);
        }
        scheduleFrame();
      });
    };

    const pauseAnimation = () => {
      if (pausedAt === null) {
        pausedAt = performance.now();
      }
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
        frameId = null;
      }
    };

    const resumeAnimation = () => {
      const now = performance.now();
      if (pausedAt !== null) {
        const pauseDuration = now - pausedAt;
        if (traceRef.current) {
          traceRef.current.startedAt += pauseDuration;
        }
        if (Number.isFinite(nextAutonomousTraceAt)) {
          nextAutonomousTraceAt += pauseDuration;
        }
        pausedAt = null;
      }
      draw(now);
      scheduleFrame();
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      size.width = Math.max(1, Math.round(bounds.width));
      size.height = Math.max(1, Math.round(bounds.height));
      size.dpr = dpr;
      canvas.width = Math.round(size.width * dpr);
      canvas.height = Math.round(size.height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      graphRef.current = graphForViewport(window.innerWidth);
      traceRef.current = null;
      labelNodeId = null;
      labelOpacity = 0;
      nextAutonomousTraceAt = performance.now() + 2600 + autonomousRandom() * 2400;
      draw(performance.now());
      scheduleFrame();
    };

    const traceFrom = (startId: number, mode: "autonomous" | "user", startedAt = performance.now()) => {
      const graph = graphRef.current;
      const random = createRandom(0x4b4e4f57 + startId * 31 + Math.round(startedAt));
      const path = [startId];
      const visited = new Set(path);
      const desiredLength = mode === "user" ? 6 + Math.floor(random() * 5) : 4 + Math.floor(random() * 6);

      const extendPath = (currentId: number): boolean => {
        if (path.length >= desiredLength) {
          return true;
        }
        const candidates = graph.nodes[currentId].neighbors
          .filter((neighbor) => !visited.has(neighbor))
          .sort(() => random() - 0.5);
        for (const nextId of candidates) {
          path.push(nextId);
          visited.add(nextId);
          if (extendPath(nextId)) {
            return true;
          }
          path.pop();
          visited.delete(nextId);
        }
        return false;
      };

      extendPath(startId);
      const propagationDuration = mode === "user" ? 1100 : 950 + random() * 650;
      const trace: TraceState = {
        path,
        startedAt,
        stepDuration: propagationDuration / Math.max(1, path.length - 1),
        holdDuration: mode === "user" ? 680 : 450 + random() * 420,
        fadeDuration: mode === "user" ? 760 : 650 + random() * 450,
        color: mode === "autonomous" && autonomousRandom() < 0.12 ? "rust" : "ink",
        mode,
      };
      traceRef.current = trace;
      nextAutonomousTraceAt = mode === "autonomous" ? startedAt + 2500 + autonomousRandom() * 2500 : Number.POSITIVE_INFINITY;
      if (traceTimeout !== null) {
        window.clearTimeout(traceTimeout);
      }
      if (reduceMotion) {
        traceTimeout = window.setTimeout(() => {
          traceRef.current = null;
          draw(performance.now());
        }, trace.holdDuration);
      }
      draw(performance.now());
      scheduleFrame();
    };

    const updatePointer = (event: PointerEvent) => {
      const bounds = canvas.getBoundingClientRect();
      pointer.targetX = event.clientX - bounds.left;
      pointer.targetY = event.clientY - bounds.top;
      if (!pointer.inside) {
        pointer.x = pointer.targetX;
        pointer.y = pointer.targetY;
      }
      pointer.inside = true;
      if (reduceMotion) {
        draw(performance.now());
      }
    };

    const onPointerLeave = () => {
      pointer.inside = false;
      pointer.hoveredId = null;
      if (reduceMotion) {
        draw(performance.now());
      }
    };

    const onPointerDown = (event: PointerEvent) => {
      updatePointer(event);
      let closest: NetworkNode | null = null;
      let closestDistance = 64;
      for (const node of graphRef.current.nodes) {
        const nodeDistance = distance(node.x, node.y, pointer.targetX, pointer.targetY);
        if (nodeDistance < closestDistance) {
          closest = node;
          closestDistance = nodeDistance;
        }
      }
      if (closest) {
        traceFrom(closest.id, "user");
      }
    };

    const onVisibilityChange = () => {
      if (document.visibilityState !== "visible") {
        pauseAnimation();
      } else if (inView) {
        resumeAnimation();
      }
    };

    const resizeObserver = new ResizeObserver(resize);
    const intersectionObserver = new IntersectionObserver(
      ([entry]) => {
        inView = entry.isIntersecting;
        if (!inView) {
          pauseAnimation();
        } else if (document.visibilityState === "visible") {
          resumeAnimation();
        }
      },
      { threshold: 0.05 },
    );

    resizeObserver.observe(canvas);
    intersectionObserver.observe(canvas);
    canvas.addEventListener("pointermove", updatePointer, { passive: true });
    canvas.addEventListener("pointerenter", updatePointer, { passive: true });
    canvas.addEventListener("pointerleave", onPointerLeave, { passive: true });
    canvas.addEventListener("pointerdown", onPointerDown, { passive: true });
    document.addEventListener("visibilitychange", onVisibilityChange);
    resize();

    return () => {
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
      }
      if (traceTimeout !== null) {
        window.clearTimeout(traceTimeout);
      }
      resizeObserver.disconnect();
      intersectionObserver.disconnect();
      canvas.removeEventListener("pointermove", updatePointer);
      canvas.removeEventListener("pointerenter", updatePointer);
      canvas.removeEventListener("pointerleave", onPointerLeave);
      canvas.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, []);

  return <canvas ref={canvasRef} className="hero-knowledge-canvas" aria-hidden="true" />;
}
