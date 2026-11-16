"use client";

import { useRef, useState, useCallback } from "react";
import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";

// MediaPipe Pose 33点のうち角度計算に使う関節インデックス
const LM = {
  leftShoulder: 11, rightShoulder: 12,
  leftElbow: 13, rightElbow: 14,
  leftWrist: 15, rightWrist: 16,
  leftHip: 23, rightHip: 24,
  leftKnee: 25, rightKnee: 26,
  leftAnkle: 27, rightAnkle: 28,
} as const;

const BONES: Array<[number, number]> = [
  [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 12], [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [24, 26], [26, 28],
];

// backend/src/api/websocket_stream.py の _calc_knee_angle と同じ
// （2D座標でのベクトル内積→acos）方式で角度を計算する
function jointAngle(
  a: { x: number; y: number },
  b: { x: number; y: number },
  c: { x: number; y: number },
): number | null {
  const v1x = a.x - b.x, v1y = a.y - b.y;
  const v2x = c.x - b.x, v2y = c.y - b.y;
  const n1 = Math.hypot(v1x, v1y), n2 = Math.hypot(v2x, v2y);
  if (n1 < 1e-6 || n2 < 1e-6) return null;
  const cos = (v1x * v2x + v1y * v2y) / (n1 * n2);
  return Math.round((Math.acos(Math.min(1, Math.max(-1, cos))) * 180) / Math.PI * 10) / 10;
}

type Angles = Record<string, number | null>;

function computeAngles(lms: Array<{ x: number; y: number }>): Angles {
  return {
    左膝: jointAngle(lms[LM.leftHip], lms[LM.leftKnee], lms[LM.leftAnkle]),
    右膝: jointAngle(lms[LM.rightHip], lms[LM.rightKnee], lms[LM.rightAnkle]),
    左股: jointAngle(lms[LM.leftShoulder], lms[LM.leftHip], lms[LM.leftKnee]),
    右股: jointAngle(lms[LM.rightShoulder], lms[LM.rightHip], lms[LM.rightKnee]),
    左肘: jointAngle(lms[LM.leftShoulder], lms[LM.leftElbow], lms[LM.leftWrist]),
    右肘: jointAngle(lms[LM.rightShoulder], lms[LM.rightElbow], lms[LM.rightWrist]),
  };
}

const MODEL_URL =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
const WASM_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.3/wasm";

export default function ClientInferenceLab() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const landmarkerRef = useRef<PoseLandmarker | null>(null);
  const rafRef = useRef<number>(0);
  const lastTsRef = useRef<number>(-1);
  const lastFpsTimeRef = useRef<number>(0);
  const runningRef = useRef(false);

  const [status, setStatus] = useState<string>("未起動");
  const [angles, setAngles] = useState<Angles>({});
  const [fps, setFps] = useState<number | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    runningRef.current = false;
    cancelAnimationFrame(rafRef.current);
    const stream = videoRef.current?.srcObject as MediaStream | null;
    stream?.getTracks().forEach(t => t.stop());
    setStatus("停止中");
  }, []);

  const loop = useCallback(() => {
    if (!runningRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const lm = landmarkerRef.current;
    if (!video || !canvas || !lm) return;
    if (video.readyState >= 2 && video.currentTime !== lastTsRef.current) {
      lastTsRef.current = video.currentTime;
      const t0 = performance.now();
      const result = lm.detectForVideo(video, t0);
      const t1 = performance.now();
      setLatency(Math.round((t1 - t0) * 10) / 10);
      const dt = t1 - lastFpsTimeRef.current;
      lastFpsTimeRef.current = t1;
      setFps(dt > 0 ? Math.round((1000 / dt) * 10) / 10 : null);
      const lms = result.landmarks?.[0];
      if (lms) {
        setAngles(computeAngles(lms));
        // 描画（正規化座標 → canvas）
        const ctx = canvas.getContext("2d");
        if (ctx) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = "rgba(96,165,250,0.9)";
          for (const p of lms) {
            ctx.beginPath();
            ctx.arc(p.x * canvas.width, p.y * canvas.height, 2.5, 0, Math.PI * 2);
            ctx.fill();
          }
          ctx.strokeStyle = "rgba(96,165,250,0.4)";
          ctx.lineWidth = 1.5;
          for (const [i, j] of BONES) {
            ctx.beginPath();
            ctx.moveTo(lms[i].x * canvas.width, lms[i].y * canvas.height);
            ctx.lineTo(lms[j].x * canvas.width, lms[j].y * canvas.height);
            ctx.stroke();
          }
        }
      }
    }
    rafRef.current = requestAnimationFrame(loop);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      setStatus("モデル読み込み中…");
      const fileset = await FilesetResolver.forVisionTasks(WASM_URL);
      landmarkerRef.current = await PoseLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL_URL, delegate: "GPU" },
        runningMode: "VIDEO",
        numPoses: 1,
      });
      setStatus("カメラ起動中…");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      const video = videoRef.current!;
      video.srcObject = stream;
      await video.play();
      canvasRef.current!.width = video.videoWidth || 640;
      canvasRef.current!.height = video.videoHeight || 480;
      runningRef.current = true;
      lastFpsTimeRef.current = performance.now();
      setFps(null);
      setStatus("解析中（ブラウザ内で完結）");
      rafRef.current = requestAnimationFrame(loop);
    } catch (e) {
      setError(String(e));
      setStatus("失敗");
    }
  }, [loop]);

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        {!runningRef.current ? (
          <button
            onClick={start}
            className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg"
          >
            カメラで開始
          </button>
        ) : (
          <button
            onClick={stop}
            className="text-xs bg-[#333] hover:bg-[#444] text-white px-4 py-2 rounded-lg"
          >
            停止
          </button>
        )}
        <span className="text-xs text-[#888] self-center">{status}</span>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <div className="relative inline-block">
        <video
          ref={videoRef}
          className="rounded-xl border border-[#1a1a1a]"
          style={{ transform: "scaleX(-1)" }}
          width={640}
          height={480}
          playsInline
          muted
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full"
          style={{ transform: "scaleX(-1)" }}
        />
      </div>
      <div className="text-xs text-[#888] space-y-1">
        <p>推論レイテンシ: {latency != null ? `${latency} ms` : "—"} ／ 表示FPS: {fps ?? "—"}</p>
        <div className="grid grid-cols-3 gap-2 max-w-sm">
          {Object.entries(angles).map(([name, v]) => (
            <div key={name} className="border border-[#1a1a1a] rounded-lg px-3 py-2 bg-[#0a0a0a]">
              <p className="text-[10px] text-[#555]">{name}</p>
              <p className="text-sm text-white">{v != null ? `${v}°` : "—"}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
