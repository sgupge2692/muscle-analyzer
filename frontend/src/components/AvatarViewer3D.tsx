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
  // 脊椎中心線（合成）
  ["left_shoulder",  "left_hip"],
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
  ["left_eye",       "left_ear"],
  ["right_eye",      "right_ear"],
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
  Shoulder:   [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
};

type Props = {
  frames: FrameLandmarks3D[];
  activations?: Record<string, number>; // 現フレームの筋肉活動強度
};

/** 筋肉活動強度 (0〜1) → RGB色オブジェクト */
function activationToRGB(act: number): { r: number; g: number; b: number } {
  const r = Math.round(80 + act * 175);
  const g = Math.round(80 - act * 70);
  const b = Math.round(80 - act * 70);
  return { r, g, b };
}

export function AvatarViewer3D({ frames, activations = {} }: Props) {
  const canvasRef    = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const frameIdxRef  = useRef(0);
  const playingRef   = useRef(false);
  const rotationRef  = useRef({ x: 0.3, y: 0 });
  const zoomRef      = useRef(1.0);  // ズーム倍率 (0.5〜3.0)
  const dragRef      = useRef<{ active: boolean; lastX: number; lastY: number }>({
    active: false, lastX: 0, lastY: 0,
  });
  // ピンチズーム用
  const pinchRef = useRef<{ active: boolean; lastDist: number }>({
    active: false, lastDist: 0,
  });
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying]   = useState(false);

  // ボーンの筋肉活動強度を計算（最大値を返す）
  const getBoneActivation = useCallback((bonePair: [string, string]): number => {
    let maxAct = 0;
    for (const [muscle, bones] of Object.entries(MUSCLE_TO_BONES)) {
      if (bones.some(([a, b]) => a === bonePair[0] && b === bonePair[1])) {
        maxAct = Math.max(maxAct, activations[muscle] ?? 0);
      }
    }
    return maxAct;
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

    const rx = rotationRef.current.x;
    const ry = rotationRef.current.y;
    const zoom = zoomRef.current;

    // 3D→2D投影（透視投影 + ズーム）
    const project = (x: number, y: number, z: number): [number, number, number] => {
      // Y軸回転
      const x1 =  x * Math.cos(ry) + z * Math.sin(ry);
      const z1 = -x * Math.sin(ry) + z * Math.cos(ry);
      // X軸回転
      const y2 =  y * Math.cos(rx) - z1 * Math.sin(rx);
      const z2 =  y * Math.sin(rx) + z1 * Math.cos(rx);
      const fov = 4.0;
      const scale = (fov / (fov + z2)) * zoom;
      return [
        W / 2 + x1 * scale * W * 0.45,
        H / 2 - y2 * scale * H * 0.45,  // MediaPipeはY軸下向きなので反転
        z2,  // 深度情報を返す（深度ソート用）
      ];
    };

    // ── ボーンを深度ソートして奥→手前の順に描画 ──
    const boneRenderList: Array<{
      ax: number; ay: number; bx: number; by: number;
      depth: number; act: number;
    }> = [];

    for (const [a, b] of BONES) {
      const pa = lm[a];
      const pb = lm[b];
      if (!pa || !pb) continue;

      const [ax, ay, az] = project(pa.x, -pa.y, pa.z);
      const [bx, by, bz] = project(pb.x, -pb.y, pb.z);
      const depth = (az + bz) / 2;  // ボーン中心の深度
      const act = getBoneActivation([a, b]);

      boneRenderList.push({ ax, ay, bx, by, depth, act });
    }

    // 奥（深度大）→手前（深度小）の順にソート
    boneRenderList.sort((a, b) => b.depth - a.depth);

    // ボーン描画（グラデーション + 活動強度に応じた太さ）
    for (const { ax, ay, bx, by, act } of boneRenderList) {
      const rgb = activationToRGB(act);
      const baseColor = act < 0.05
        ? { r: 58, g: 58, b: 58 }
        : rgb;

      // グラデーション（始点→終点の色変化）
      const grad = ctx.createLinearGradient(ax, ay, bx, by);
      grad.addColorStop(0, `rgb(${baseColor.r},${baseColor.g},${baseColor.b})`);
      grad.addColorStop(1, `rgb(${Math.max(20, baseColor.r - 30)},${Math.max(10, baseColor.g - 20)},${Math.max(10, baseColor.b - 20)})`);

      // 筋肉活動強度に応じた線幅 (1.5〜6.0)
      const lineWidth = 1.5 + act * 4.5;

      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.strokeStyle = grad;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.stroke();
    }

    // 関節点を描画（活動強度に応じてサイズ変化）
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

      // 周辺ボーンの活動強度に応じてドットサイズ変化 (3〜7px)
      const relatedAct = Math.max(
        ...Object.values(MUSCLE_TO_BONES)
          .flat()
          .filter(([a, b]) => a === name || b === name)
          .map(() => 0),
        0,
      );
      const dotRadius = 3 + relatedAct * 4;

      ctx.beginPath();
      ctx.arc(px, py, dotRadius, 0, Math.PI * 2);
      ctx.fillStyle = "#ffffff";
      ctx.fill();

      // アクティブな関節にはアウトライン
      if (relatedAct > 0.3) {
        ctx.beginPath();
        ctx.arc(px, py, dotRadius + 2, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(239,68,68,${relatedAct * 0.6})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }
  }, [frames, getBoneActivation]);

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

  // ResizeObserver でCanvasをコンテナに追従させる
  useEffect(() => {
    const container = containerRef.current;
    const canvas    = canvasRef.current;
    if (!container || !canvas) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        // アスペクト比 3:4 を維持
        canvas.width  = Math.floor(width);
        canvas.height = Math.floor(width * (4 / 3));
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

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

  // マウスホイールでズーム
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    zoomRef.current = Math.max(0.5, Math.min(3.0, zoomRef.current + delta));
  };

  // タッチ操作（スマホ対応）
  const onTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      // ピンチズーム開始
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      pinchRef.current = { active: true, lastDist: Math.hypot(dx, dy) };
    } else {
      const t = e.touches[0];
      dragRef.current = { active: true, lastX: t.clientX, lastY: t.clientY };
    }
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && pinchRef.current.active) {
      // ピンチズーム処理
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const scale = dist / (pinchRef.current.lastDist || dist);
      zoomRef.current = Math.max(0.5, Math.min(3.0, zoomRef.current * scale));
      pinchRef.current.lastDist = dist;
    } else if (dragRef.current.active && e.touches.length === 1) {
      // 1本指ドラッグで回転
      const t = e.touches[0];
      const dx = t.clientX - dragRef.current.lastX;
      const dy = t.clientY - dragRef.current.lastY;
      rotationRef.current.y += dx * 0.01;
      rotationRef.current.x += dy * 0.01;
      dragRef.current.lastX = t.clientX;
      dragRef.current.lastY = t.clientY;
    }
  };
  const onTouchEnd = () => {
    dragRef.current.active = false;
    pinchRef.current.active = false;
  };

  const togglePlay = () => {
    playingRef.current = !playingRef.current;
    setPlaying(playingRef.current);
  };
  const onSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = Number(e.target.value);
    frameIdxRef.current = idx;
    setFrameIdx(idx);
  };
  const onResetView = () => {
    rotationRef.current = { x: 0.3, y: 0 };
    zoomRef.current = 1.0;
  };

  return (
    <div className="flex flex-col items-center gap-3 w-full">
      <div ref={containerRef} className="w-full">
        <canvas
          ref={canvasRef}
          width={300}
          height={400}
          className="w-full rounded-2xl bg-[#0a0a0a] cursor-grab active:cursor-grabbing"
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseUp}
          onWheel={onWheel}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        />
      </div>
      <div className="flex items-center gap-3 w-full">
        <button
          onClick={togglePlay}
          className="px-3 py-1 rounded-lg bg-[#1e1e1e] text-white text-xs hover:bg-[#2a2a2a] transition-colors flex-shrink-0"
        >
          {playing ? "⏸ 停止" : "▶ 再生"}
        </button>
        <input
          type="range" min={0} max={Math.max(0, frames.length - 1)}
          value={frameIdx}
          onChange={onSeek}
          className="flex-1 accent-red-500"
        />
        <span className="text-[#555] text-xs font-mono w-16 text-right flex-shrink-0">
          {frameIdx}/{frames.length}
        </span>
      </div>
      <div className="flex items-center gap-4 w-full">
        <p className="text-[#444] text-[10px] flex-1">
          ドラッグで回転 / ホイールorピンチでズーム
        </p>
        <button
          onClick={onResetView}
          className="text-[#333] text-[10px] hover:text-[#666] transition-colors"
        >
          ビューをリセット
        </button>
      </div>
    </div>
  );
}
