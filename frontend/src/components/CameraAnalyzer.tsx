"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { ActivationMap } from "@/types/analysis";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type PoseResult = {
  type: "pose" | "no_pose" | "error";
  frame?: number;
  landmarks?: Record<string, { x: number; y: number; z: number; v: number }>;
  world?: Record<string, { x: number; y: number; z: number }>;
  knee_angle?: { left: number | null; right: number | null };
  activations?: ActivationMap;
  fps?: number;
  message?: string;
};

const MUSCLE_NAMES_JA: Record<string, string> = {
  Quadriceps: "大腿四頭筋", Gluteus: "大臀筋", Hamstring: "ハムストリング",
  Lower_Back: "脊柱起立筋", Calves: "下腿三頭筋", Inner_Thigh: "内転筋",
};

type Props = {
  exercise: string;
  onCapture?: (blob: Blob) => void;
};

export function CameraAnalyzer({ exercise, onCapture }: Props) {
  const videoRef    = useRef<HTMLVideoElement | null>(null);
  const canvasRef   = useRef<HTMLCanvasElement | null>(null);
  const wsRef       = useRef<WebSocket | null>(null);
  const rafRef      = useRef<number>(0);
  const streamRef   = useRef<MediaStream | null>(null);

  const [status,      setStatus]      = useState<"idle" | "connecting" | "active" | "error">("idle");
  const [fps,         setFps]         = useState<number>(0);
  const [kneeAngle,   setKneeAngle]   = useState<{ left: number | null; right: number | null } | null>(null);
  const [activations, setActivations] = useState<ActivationMap>({});
  const [errorMsg,    setErrorMsg]    = useState<string>("");

  // スケルトンを描画
  const drawSkeleton = useCallback((
    ctx: CanvasRenderingContext2D,
    landmarks: PoseResult["landmarks"],
    w: number, h: number
  ) => {
    if (!landmarks) return;
    const CONNECTIONS: [string, string][] = [
      ["left_shoulder","right_shoulder"],
      ["left_shoulder","left_hip"], ["right_shoulder","right_hip"],
      ["left_hip","right_hip"],
      ["left_shoulder","left_elbow"], ["left_elbow","left_wrist"],
      ["right_shoulder","right_elbow"], ["right_elbow","right_wrist"],
      ["left_hip","left_knee"], ["left_knee","left_ankle"],
      ["right_hip","right_knee"], ["right_knee","right_ankle"],
    ];
    ctx.strokeStyle = "rgba(239,68,68,0.8)";
    ctx.lineWidth   = 3;
    ctx.lineCap     = "round";
    for (const [a, b] of CONNECTIONS) {
      const pa = landmarks[a], pb = landmarks[b];
      if (!pa || !pb || pa.v < 0.5 || pb.v < 0.5) continue;
      ctx.beginPath();
      ctx.moveTo(pa.x * w, pa.y * h);
      ctx.lineTo(pb.x * w, pb.y * h);
      ctx.stroke();
    }
    // 関節点
    ctx.fillStyle = "#ffffff";
    for (const lm of Object.values(landmarks)) {
      if (lm.v < 0.5) continue;
      ctx.beginPath();
      ctx.arc(lm.x * w, lm.y * h, 4, 0, Math.PI * 2);
      ctx.fill();
    }
  }, []);

  // フレーム送信ループ
  const sendLoop = useCallback(() => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    const ws     = wsRef.current;
    if (!video || !canvas || !ws || ws.readyState !== WebSocket.OPEN) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;

    ctx.drawImage(video, 0, 0);

    // base64エンコードして送信
    const b64 = canvas.toDataURL("image/jpeg", 0.7).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", data: b64 }));

    rafRef.current = requestAnimationFrame(sendLoop);
  }, []);

  // WebSocket接続
  const connect = useCallback(async () => {
    setStatus("connecting");
    setErrorMsg("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch (e) {
      setStatus("error");
      setErrorMsg("カメラへのアクセスが拒否されました");
      return;
    }

    const ws = new WebSocket(`${WS_URL}/ws/stream?exercise=${exercise}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("active");
      rafRef.current = requestAnimationFrame(sendLoop);
    };

    ws.onmessage = (e) => {
      const result: PoseResult = JSON.parse(e.data);
      if (result.type === "pose") {
        if (result.fps)         setFps(result.fps);
        if (result.knee_angle)  setKneeAngle(result.knee_angle);
        if (result.activations) setActivations(result.activations);

        // スケルトンをオーバーレイ描画
        const canvas = canvasRef.current;
        if (canvas && result.landmarks) {
          const ctx = canvas.getContext("2d");
          if (ctx) drawSkeleton(ctx, result.landmarks, canvas.width, canvas.height);
        }
      }
    };

    ws.onerror = () => {
      setStatus("error");
      setErrorMsg("バックエンドに接続できません");
    };

    ws.onclose = () => {
      if (status === "active") setStatus("idle");
      cancelAnimationFrame(rafRef.current);
    };
  }, [exercise, sendLoop, drawSkeleton, status]);

  // 停止
  const disconnect = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    wsRef.current?.close();
    streamRef.current?.getTracks().forEach(t => t.stop());
    setStatus("idle");
    setActivations({});
    setKneeAngle(null);
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  const sorted = Object.entries(activations).sort((a, b) => b[1] - a[1]).slice(0, 6);

  return (
    <div className="space-y-4">
      {/* カメラビュー */}
      <div className="relative bg-[#080808] rounded-2xl overflow-hidden aspect-video">
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          muted playsInline
          style={{ transform: "scaleX(-1)" }}
        />
        <canvas
          ref={canvasRef}
          className="absolute inset-0 w-full h-full"
          style={{ transform: "scaleX(-1)" }}
        />

        {/* ステータスバッジ */}
        <div className="absolute top-3 left-3 flex items-center gap-2">
          {status === "active" && (
            <>
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="text-[10px] text-white font-bold tracking-wider bg-black/60 px-2 py-0.5 rounded-full">
                LIVE
              </span>
              <span className="text-[10px] text-[#888] bg-black/60 px-2 py-0.5 rounded-full font-mono">
                {fps} fps
              </span>
            </>
          )}
          {status === "connecting" && (
            <span className="text-[10px] text-yellow-400 bg-black/60 px-2 py-0.5 rounded-full">接続中...</span>
          )}
        </div>

        {/* 膝角度オーバーレイ */}
        {kneeAngle && status === "active" && (
          <div className="absolute bottom-3 left-3 flex gap-2">
            {(["left", "right"] as const).map(side => (
              kneeAngle[side] !== null && (
                <div key={side} className="bg-black/70 px-2 py-1 rounded-lg">
                  <p className="text-[9px] text-[#666]">{side === "left" ? "左膝" : "右膝"}</p>
                  <p className="text-white font-mono font-bold text-sm">{kneeAngle[side]}°</p>
                </div>
              )
            ))}
          </div>
        )}

        {/* アイドル状態 */}
        {status === "idle" && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40">
            <div className="text-center">
              <div className="w-12 h-12 rounded-full border-2 border-[#333] flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-[#555]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-[#555] text-xs">カメラを起動して解析を開始</p>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
            <p className="text-red-400 text-xs text-center px-4">{errorMsg}</p>
          </div>
        )}
      </div>

      {/* コントロール */}
      <div className="flex gap-2">
        {status !== "active" ? (
          <button
            onClick={connect}
            disabled={status === "connecting"}
            className="flex-1 py-3 rounded-2xl bg-red-600 text-white text-xs font-bold
              tracking-[0.15em] hover:bg-red-500 transition-colors disabled:opacity-50"
          >
            {status === "connecting" ? "接続中..." : "▶ リアルタイム解析を開始"}
          </button>
        ) : (
          <button
            onClick={disconnect}
            className="flex-1 py-3 rounded-2xl bg-[#1a1a1a] text-white text-xs font-bold
              tracking-[0.15em] hover:bg-[#222] transition-colors border border-[#2a2a2a]"
          >
            ⏹ 停止
          </button>
        )}
      </div>

      {/* リアルタイム筋肉活動 */}
      {sorted.length > 0 && (
        <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-2xl p-4 space-y-3">
          <p className="text-[10px] tracking-[0.2em] text-[#444] font-bold">REALTIME ACTIVATION</p>
          {sorted.map(([name, val], i) => (
            <div key={name}>
              <div className="flex justify-between items-baseline mb-1">
                <span className={`text-xs ${i === 0 ? "text-white font-medium" : "text-[#555]"}`}>
                  {MUSCLE_NAMES_JA[name] ?? name}
                </span>
                <span className={`font-mono text-xs ${i === 0 ? "text-white" : "text-[#444]"}`}>
                  {(val * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-1 bg-[#111] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${val * 100}%`,
                    background: i === 0
                      ? "linear-gradient(90deg, #7f1d1d, #ef4444)"
                      : "linear-gradient(90deg, #1c1c1c, #333)",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
