"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { FrameLandmarks3D } from "@/types/analysis";

// MediaPipeの骨格ボーン定義（接続する関節ペア）
const BONES: [string, string][] = [
  // 胴体
  ["left_shoulder",  "right_shoulder"],
  ["left_shoulder",  "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip",       "right_hip"],
  // 左腕
  ["left_shoulder",  "left_elbow"],
  ["left_elbow",     "left_wrist"],
  // 右腕
  ["right_shoulder", "right_elbow"],
  ["right_elbow",    "right_wrist"],
  // 左脚
  ["left_hip",       "left_knee"],
  ["left_knee",      "left_ankle"],
  ["left_ankle",     "left_heel"],
  ["left_ankle",     "left_foot_index"],
  // 右脚
  ["right_hip",      "right_knee"],
  ["right_knee",     "right_ankle"],
  ["right_ankle",    "right_heel"],
  ["right_ankle",    "right_foot_index"],
  // 顔（簡略）
  ["nose",           "left_eye"],
  ["nose",           "right_eye"],
];

// 筋肉名→対応ボーンのマッピング（ヒートマップ色付け用）
const MUSCLE_TO_BONES: Record<string, [string, string][]> = {
  Quadriceps: [["left_hip", "left_knee"],   ["right_hip", "right_knee"]],
  Hamstring:  [["left_hip", "left_knee"],   ["right_hip", "right_knee"]],
  Gluteus:    [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
  Calves:     [["left_knee", "left_ankle"],  ["right_knee", "right_ankle"]],
  Lower_Back: [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
  Chest:      [["left_shoulder", "right_shoulder"]],
  Triceps:    [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
  Biceps:     [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
  Latissimus: [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
};

type Props = {
  frames: FrameLandmarks3D[];
  activations?: Record<string, number>; // 現フレームの筋肉活動強度
};

export function AvatarViewer3D({ frames, activations = {} }: Props) {
  const canvasRef    = useRef<HTMLCanvasElement | null>(null);
  const frameIdxRef  = useRef(0);
  const playingRef   = useRef(false);
  const rotationRef  = useRef({ x: 0.3, y: 0 });
  const dragRef      = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false, lastX: 0, lastY: 0,
  });
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying]   = useState(false);

  // 筋肉活動強度→色（赤系）
  const activationColor = useCallback((bonePair: [string, string]): string => {
    let maxAct = 0;
    for (const [muscle, bones] of Object.entries(MUSCLE_TO_BONES)) {
      if (bones.some(([a, b]) => a === bonePair[0] && b === bonePair[1])) {
        maxAct = Math.max(maxAct, activations[muscle] ?? 0);
      }
    }
    if (maxAct < 0.05) return "#3a3a3a";
    const r = Math.round(80  + maxAct * 175);
    const g = Math.round(80  - maxAct * 70);
    const b = Math.round(80  - maxAct * 70);
    return `rgb(${r},${g},${b})`;
  }, [activations]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || frames.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const lm = frames[frameIdxRef.current]?.landmarks;
    if (!lm) return;

    // 3D→2D投影（簡易透視投影）
    const rx = rotationRef.current.x;
    const ry = rotationRef.current.y;
    const project = (x: number, y: number, z: number): [number, number] => {
      // Y軸回転
      const x1 =  x * Math.cos(ry) + z * Math.sin(ry);
      const z1 = -x * Math.sin(ry) + z * Math.cos(ry);
      // X軸回転
      const y2 =  y * Math.cos(rx) - z1 * Math.sin(rx);
      const z2 =  y * Math.sin(rx) + z1 * Math.cos(rx);
      const fov = 4.0;
      const scale = fov / (fov + z2);
      return [
        W / 2 + x1 * scale * W * 0.45,
        H / 2 - y2 * scale * H * 0.45,  // MediaPipeはY軸下向きなので反転
      ];
    };

    // ボーンを描画
    for (const [a, b] of BONES) {
      const pa = lm[a];
      const pb = lm[b];
      if (!pa || !pb) continue;

      const [ax, ay] = project(pa.x, -pa.y, pa.z);  // Y反転
      const [bx, by] = project(pb.x, -pb.y, pb.z);

      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.strokeStyle = activationColor([a, b]);
      ctx.lineWidth = 3;
      ctx.lineCap = "round";
      ctx.stroke();
    }

    // 関節点を描画
    const keyJoints = [
      "nose", "left_shoulder", "right_shoulder",
      "left_elbow", "right_elbow", "left_wrist", "right_wrist",
      "left_hip", "right_hip", "left_knee", "right_knee",
      "left_ankle", "right_ankle",
    ];
    for (const name of keyJoints) {
      const pt = lm[name];
      if (!pt) continue;
      const [px, py] = project(pt.x, -pt.y, pt.z);
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
    }
  }, [frames, activationColor]);

  // アニメーションループ
  useEffect(() => {
    let raf: number;
    let last = 0;
    const FPS = 30;

    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      if (playingRef.current && now - last > 1000 / FPS) {
        frameIdxRef.current = (frameIdxRef.current + 1) % frames.length;
        setFrameIdx(frameIdxRef.current);
        last = now;
      }
      draw();
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [frames, draw]);

  // マウスドラッグで視点回転
  const onMouseDown = (e: React.MouseEvent) => {
    dragRef.current = { active: true, lastX: e.clientX, lastY: e.clientY };
  };
  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragRef.current.active) return;
    const dx = e.clientX - dragRef.current.lastX;
    const dy = e.clientY - dragRef.current.lastY;
    rotationRef.current.y += dx * 0.01;
    rotationRef.current.x += dy * 0.01;
    dragRef.current.lastX = e.clientX;
    dragRef.current.lastY = e.clientY;
  };
  const onMouseUp = () => { dragRef.current.active = false; };

  // タッチ操作（スマホ対応）
  const onTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    dragRef.current = { active: true, lastX: t.clientX, lastY: t.clientY };
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (!dragRef.current.active) return;
    const t = e.touches[0];
    const dx = t.clientX - dragRef.current.lastX;
    const dy = t.clientY - dragRef.current.lastY;
    rotationRef.current.y += dx * 0.01;
    rotationRef.current.x += dy * 0.01;
    dragRef.current.lastX = t.clientX;
    dragRef.current.lastY = t.clientY;
  };
  const onTouchEnd = () => { dragRef.current.active = false; };

  const togglePlay = () => {
    playingRef.current = !playingRef.current;
    setPlaying(playingRef.current);
  };
  const onSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = Number(e.target.value);
    frameIdxRef.current = idx;
    setFrameIdx(idx);
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <canvas
        ref={canvasRef}
        width={300}
        height={400}
        className="rounded-2xl bg-[#0a0a0a] cursor-grab active:cursor-grabbing"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      />
      <div className="flex items-center gap-3 w-full max-w-[300px]">
        <button
          onClick={togglePlay}
          className="px-3 py-1 rounded-lg bg-[#1e1e1e] text-white text-xs hover:bg-[#2a2a2a] transition-colors"
        >
          {playing ? "⏸ 停止" : "▶ 再生"}
        </button>
        <input
          type="range" min={0} max={Math.max(0, frames.length - 1)}
          value={frameIdx}
          onChange={onSeek}
          className="flex-1 accent-red-500"
        />
        <span className="text-[#555] text-xs font-mono w-16 text-right">
          {frameIdx}/{frames.length}
        </span>
      </div>
      <p className="text-[#444] text-[10px]">ドラッグ / スワイプで視点回転</p>
    </div>
  );
}
