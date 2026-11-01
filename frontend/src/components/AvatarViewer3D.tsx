"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { FrameLandmarks3D } from "@/types/analysis";

const MUSCLE_TO_SEGMENTS: Record<string, string[]> = {
  Quadriceps:  ["left_thigh",  "right_thigh"],
  Hamstring:   ["left_thigh",  "right_thigh"],
  Gluteus:     ["pelvis"],
  Calves:      ["left_calf",   "right_calf"],
  Lower_Back:  ["torso"],
  Chest:       ["chest"],
  Triceps:     ["left_upper_arm", "right_upper_arm"],
  Biceps:      ["left_upper_arm", "right_upper_arm"],
  Latissimus:  ["torso"],
  Shoulder:    ["left_shoulder_cap", "right_shoulder_cap"],
};

type Landmark3D = { x: number; y: number; z: number };

type Props = {
  frames: FrameLandmarks3D[];
  activations?: Record<string, number>;
};

function getActivationColor(act: number, alpha = 1): string {
  if (act < 0.05) return `rgba(40,40,40,${alpha})`;
  const r = Math.round(80  + act * 175);
  const g = Math.round(80  - act * 70);
  const b = Math.round(80  - act * 70);
  return `rgba(${r},${g},${b},${alpha})`;
}

function segmentActivation(seg: string, activations: Record<string, number>): number {
  let max = 0;
  for (const [muscle, segs] of Object.entries(MUSCLE_TO_SEGMENTS)) {
    if (segs.includes(seg)) max = Math.max(max, activations[muscle] ?? 0);
  }
  return max;
}

export function AvatarViewer3D({ frames, activations = {} }: Props) {
  const canvasRef   = useRef<HTMLCanvasElement | null>(null);
  const frameIdxRef = useRef(0);
  const playingRef  = useRef(false);
  const rotYRef     = useRef(0.2);
  const rotXRef     = useRef(0.1);
  const zoomRef     = useRef(1.0);
  const dragRef     = useRef({ active: false, lastX: 0, lastY: 0 });
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing,  setPlaying]  = useState(false);

  const project = useCallback((
    x: number, y: number, z: number,
    W: number, H: number
  ): [number, number, number] => {
    const ry = rotYRef.current, rx = rotXRef.current;
    const x1 =  x * Math.cos(ry) + z * Math.sin(ry);
    const z1 = -x * Math.sin(ry) + z * Math.cos(ry);
    const y2 =  y * Math.cos(rx) - z1 * Math.sin(rx);
    const z2 =  y * Math.sin(rx) + z1 * Math.cos(rx);
    const fov = 3.5 / zoomRef.current;
    const scale = fov / (fov + z2 + 2);
    return [W / 2 + x1 * scale * W * 0.45, H / 2 - y2 * scale * H * 0.45, z2];
  }, []);

  const drawCapsule = useCallback((
    ctx: CanvasRenderingContext2D,
    ax: number, ay: number,
    bx: number, by: number,
    r: number, color: string
  ) => {
    const dx = bx - ax, dy = by - ay;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    const nx = -dy / len * r, ny = dx / len * r;

    ctx.beginPath();
    ctx.moveTo(ax + nx, ay + ny);
    ctx.lineTo(bx + nx, by + ny);
    ctx.arc(bx, by, r, Math.atan2(ny, nx), Math.atan2(-ny, -nx));
    ctx.lineTo(ax - nx, ay - ny);
    ctx.arc(ax, ay, r, Math.atan2(-ny, -nx), Math.atan2(ny, nx));
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "rgba(0,0,0,0.3)";
    ctx.lineWidth   = 0.5;
    ctx.stroke();
  }, []);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || frames.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const lm = frames[frameIdxRef.current]?.landmarks;
    if (!lm) return;

    const P = (name: string): [number, number, number] | null => {
      const pt = lm[name];
      if (!pt) return null;
      return project(pt.x, -pt.y, pt.z, W, H);
    };

    const seg = (segName: string) => getActivationColor(segmentActivation(segName, activations));
    const r = Math.max(W, H) * 0.022;  // 体の太さ（画面サイズに応じて）

    // 描画順：奥から手前
    type DrawItem = { z: number; fn: () => void };
    const items: DrawItem[] = [];

    const addCapsule = (
      aName: string, bName: string, segName: string, radiusMult = 1.0
    ) => {
      const a = P(aName), b = P(bName);
      if (!a || !b) return;
      const zAvg = (a[2] + b[2]) / 2;
      items.push({ z: zAvg, fn: () =>
        drawCapsule(ctx, a[0], a[1], b[0], b[1], r * radiusMult, seg(segName))
      });
    };

    const addCircle = (name: string, segName: string, radiusMult = 1.0) => {
      const p = P(name);
      if (!p) return;
      items.push({ z: p[2], fn: () => {
        ctx.beginPath();
        ctx.arc(p[0], p[1], r * radiusMult, 0, Math.PI * 2);
        ctx.fillStyle = seg(segName);
        ctx.fill();
        ctx.strokeStyle = "rgba(0,0,0,0.3)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }});
    };

    // 体幹
    addCapsule("left_shoulder",  "right_shoulder", "chest",  1.2);
    addCapsule("left_shoulder",  "left_hip",       "torso",  1.1);
    addCapsule("right_shoulder", "right_hip",      "torso",  1.1);
    addCapsule("left_hip",       "right_hip",      "pelvis", 1.2);

    // 腕
    addCapsule("left_shoulder",  "left_elbow",   "left_upper_arm",  0.7);
    addCapsule("left_elbow",     "left_wrist",   "left_upper_arm",  0.6);
    addCapsule("right_shoulder", "right_elbow",  "right_upper_arm", 0.7);
    addCapsule("right_elbow",    "right_wrist",  "right_upper_arm", 0.6);

    // 脚
    addCapsule("left_hip",   "left_knee",   "left_thigh",  1.0);
    addCapsule("left_knee",  "left_ankle",  "left_calf",   0.8);
    addCapsule("right_hip",  "right_knee",  "right_thigh", 1.0);
    addCapsule("right_knee", "right_ankle", "right_calf",  0.8);

    // 足
    addCapsule("left_ankle",  "left_foot_index",  "left_calf",  0.5);
    addCapsule("right_ankle", "right_foot_index", "right_calf", 0.5);

    // 関節球
    for (const [name, segName] of [
      ["left_knee",  "left_thigh"], ["right_knee",  "right_thigh"],
      ["left_elbow", "left_upper_arm"], ["right_elbow", "right_upper_arm"],
      ["left_hip",   "pelvis"],     ["right_hip",    "pelvis"],
      ["left_shoulder", "chest"],   ["right_shoulder", "chest"],
    ] as [string, string][]) {
      addCircle(name, segName, 0.85);
    }

    // 頭部
    const nose = P("nose");
    const ls   = P("left_shoulder");
    const rs   = P("right_shoulder");
    if (nose && ls && rs) {
      const headR = r * 1.6;
      const hy = nose[1] - headR * 0.4;
      items.push({ z: nose[2], fn: () => {
        ctx.beginPath();
        ctx.arc(nose[0], hy, headR, 0, Math.PI * 2);
        ctx.fillStyle = seg("chest");
        ctx.fill();
        ctx.strokeStyle = "rgba(0,0,0,0.3)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }});
      // 首
      const shoulderMidX = (ls[0] + rs[0]) / 2;
      const shoulderMidY = (ls[1] + rs[1]) / 2;
      items.push({ z: (nose[2] + ls[2]) / 2, fn: () =>
        drawCapsule(ctx, nose[0], hy + headR * 0.8, shoulderMidX, shoulderMidY, r * 0.5, seg("chest"))
      });
    }

    // z順でソートして描画（奥から手前）
    items.sort((a, b) => b.z - a.z);
    for (const item of items) item.fn();
  }, [frames, activations, project, drawCapsule]);

  // アニメーションループ
  useEffect(() => {
    let raf: number;
    let last = 0;
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      if (playingRef.current && now - last > 1000 / 30) {
        frameIdxRef.current = (frameIdxRef.current + 1) % Math.max(1, frames.length);
        setFrameIdx(frameIdxRef.current);
        last = now;
      }
      draw();
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [frames, draw]);

  // マウス操作
  const onMouseDown = (e: React.MouseEvent) =>
    (dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY });
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragRef.current.active) return;
    rotYRef.current += (e.clientX - dragRef.current.lastX) * 0.01;
    rotXRef.current += (e.clientY - dragRef.current.lastY) * 0.01;
    dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY };
  };
  const onMouseUp  = () => { dragRef.current.active = false; };
  const onWheel    = (e: React.WheelEvent) => {
    zoomRef.current = Math.max(0.5, Math.min(3.0, zoomRef.current - e.deltaY * 0.001));
  };

  // タッチ操作
  const onTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    dragRef.current = { active: true, lastX: t.clientX, lastY: t.clientY };
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (!dragRef.current.active) return;
    const t = e.touches[0];
    rotYRef.current += (t.clientX - dragRef.current.lastX) * 0.01;
    rotXRef.current += (t.clientY - dragRef.current.lastY) * 0.01;
    dragRef.current = { active: true, lastX: t.clientX, lastY: t.clientY };
  };
  const onTouchEnd = () => { dragRef.current.active = false; };

  const reset = () => {
    rotYRef.current = 0.2; rotXRef.current = 0.1; zoomRef.current = 1.0;
  };
  const toggle = () => { playingRef.current = !playingRef.current; setPlaying(p => !p); };
  const onSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    frameIdxRef.current = Number(e.target.value);
    setFrameIdx(frameIdxRef.current);
  };

  return (
    <div className="flex flex-col items-center gap-3 w-full">
      <canvas
        ref={canvasRef}
        width={320} height={420}
        className="rounded-2xl bg-[#050505] cursor-grab active:cursor-grabbing w-full max-w-[320px]"
        onMouseDown={onMouseDown} onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}    onMouseLeave={onMouseUp}
        onWheel={onWheel}
        onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}
      />
      <div className="flex items-center gap-2 w-full max-w-[320px]">
        <button onClick={toggle}
          className="px-3 py-1.5 rounded-xl bg-[#1a1a1a] text-white text-[10px] font-bold
            hover:bg-[#222] transition-colors flex-shrink-0">
          {playing ? "⏸" : "▶"}
        </button>
        <input type="range" min={0} max={Math.max(0, frames.length - 1)}
          value={frameIdx} onChange={onSeek}
          className="flex-1 accent-red-500 h-1" />
        <button onClick={reset}
          className="px-2 py-1.5 rounded-xl bg-[#1a1a1a] text-[#555] text-[10px]
            hover:text-white transition-colors flex-shrink-0">
          ↺
        </button>
      </div>
      <p className="text-[#333] text-[9px]">ドラッグ / スワイプで回転 · スクロールでズーム</p>
    </div>
  );
}
