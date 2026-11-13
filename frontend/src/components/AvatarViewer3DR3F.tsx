"use client";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import { FrameLandmarks3D } from "@/types/analysis";

// MediaPipeの骨格ボーン定義（AvatarViewer3D と同じ接続ペア）
const BONES: [string, string][] = [
  ["left_shoulder", "right_shoulder"],
  ["left_shoulder", "left_hip"],
  ["right_shoulder", "right_hip"],
  ["left_hip", "right_hip"],
  ["left_shoulder", "left_elbow"],
  ["left_elbow", "left_wrist"],
  ["right_shoulder", "right_elbow"],
  ["right_elbow", "right_wrist"],
  ["left_hip", "left_knee"],
  ["left_knee", "left_ankle"],
  ["left_ankle", "left_foot_index"],
  ["right_hip", "right_knee"],
  ["right_knee", "right_ankle"],
  ["right_ankle", "right_foot_index"],
];

// 筋肉名→対応ボーン（ヒートマップ色付け用。AvatarViewer3D と同一の対応）
const MUSCLE_TO_BONES: Record<string, [string, string][]> = {
  Quadriceps: [["left_hip", "left_knee"], ["right_hip", "right_knee"]],
  Hamstring: [["left_hip", "left_knee"], ["right_hip", "right_knee"]],
  Gluteus: [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
  Calves: [["left_knee", "left_ankle"], ["right_knee", "right_ankle"]],
  Lower_Back: [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
  Chest: [["left_shoulder", "right_shoulder"]],
  Triceps: [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
  Biceps: [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
  Latissimus: [["left_shoulder", "left_hip"], ["right_shoulder", "right_hip"]],
  Shoulder: [["left_shoulder", "left_elbow"], ["right_shoulder", "right_elbow"]],
};

const JOINT_SPHERES = [
  "nose",
  "left_shoulder", "right_shoulder",
  "left_elbow", "right_elbow", "left_wrist", "right_wrist",
  "left_hip", "right_hip",
  "left_knee", "right_knee",
  "left_ankle", "right_ankle",
];

type Props = {
  frames: FrameLandmarks3D[];
  activations?: Record<string, number>;
};

type Vec3 = { x: number; y: number; z: number };

/** MediaPipeのworld座標（y下向き）→ three.js座標（y上向き）に変換 */
function toThreePos(lm: Vec3): THREE.Vector3 {
  return new THREE.Vector3(lm.x, -lm.y, -lm.z);
}

function activationForBone(a: string, b: string, activations: Record<string, number>): number {
  let maxAct = 0;
  for (const [muscle, bones] of Object.entries(MUSCLE_TO_BONES)) {
    if (bones.some(([x, y]) => (x === a && y === b))) {
      maxAct = Math.max(maxAct, activations[muscle] ?? 0);
    }
  }
  return maxAct;
}

const UP = new THREE.Vector3(0, 1, 0);

function Segment({
  from,
  to,
  activation,
}: {
  from: THREE.Vector3;
  to: THREE.Vector3;
  activation: number;
}) {
  const { mid, quat, length } = useMemo(() => {
    const dir = new THREE.Vector3().subVectors(to, from);
    const length = Math.max(dir.length(), 0.01);
    const quat = new THREE.Quaternion().setFromUnitVectors(UP, dir.clone().normalize());
    const mid = new THREE.Vector3().addVectors(from, to).multiplyScalar(0.5);
    return { mid, quat, length };
  }, [from, to]);

  const radius = 0.028 + activation * 0.02;
  // 活動強度で発色（低: 暗灰 → 高: 赤）
  const color = new THREE.Color().setRGB(
    0.18 + activation * 0.8,
    0.18 - activation * 0.12,
    0.18 - activation * 0.12,
  );
  return (
    <mesh position={mid} quaternion={quat}>
      <capsuleGeometry args={[radius, length, 4, 10]} />
      <meshStandardMaterial color={color} emissive={new THREE.Color().setRGB(activation * 0.5, 0, 0)} emissiveIntensity={activation > 0.05 ? 0.6 : 0} />
    </mesh>
  );
}

function Joint({ pos, size }: { pos: THREE.Vector3; size: number }) {
  return (
    <mesh position={pos}>
      <sphereGeometry args={[size, 12, 12]} />
      <meshStandardMaterial color="#e8e8e8" roughness={0.4} />
    </mesh>
  );
}

function Scene({ frames, activations, frameIdx, playing, setFrameIdx }: {
  frames: FrameLandmarks3D[];
  activations: Record<string, number>;
  frameIdx: number;
  playing: boolean;
  setFrameIdx: (i: number) => void;
}) {
  const accRef = useRef(0);

  useFrame((_, delta) => {
    if (playing && frames.length > 0) {
      accRef.current += delta * 30; // 30fpsで再生
      if (accRef.current >= 1) {
        accRef.current = 0;
        setFrameIdx((frameIdx + 1) % frames.length);
      }
    }
  });

  if (frames.length === 0) {
    return (
      <mesh>
        <boxGeometry args={[0.01, 0.01, 0.01]} />
        <meshBasicMaterial visible={false} />
      </mesh>
    );
  }

  const lm = frames[Math.min(frameIdx, frames.length - 1)]?.landmarks;
  if (!lm) return null;

  const get = (name: string): THREE.Vector3 | null =>
    lm[name] ? toThreePos(lm[name]) : null;

  const elements: ReactNode[] = [];
  for (const [a, b] of BONES) {
    const pa = get(a);
    const pb = get(b);
    if (!pa || !pb) continue;
    const act = activationForBone(a, b, activations);
    elements.push(<Segment key={`${a}-${b}`} from={pa} to={pb} activation={act} />);
  }
  for (const name of JOINT_SPHERES) {
    const p = get(name);
    if (!p) continue;
    elements.push(<Joint key={name} pos={p} size={name === "nose" ? 0.045 : 0.022} />);
  }

  return <group>{elements}</group>;
}

/**
 * React Three Fiber 版 3Dモーションビューア（トラックB フェーズ1プロトタイプ）
 *
 * 旧 AvatarViewer3D（2Dキャンバス投影の棒人間）を置き換える:
 *  - 棒人間ではなくカプセルメッシュの人型が MediaPipe の world_landmarks に
 *    追従して動く
 *  - 筋肉活動強度に応じて体幹・四肢のメッシュが赤く発光する
 *  - 回転・ズームは OrbitControls（マウス/タッチ両対応）
 */
export function AvatarViewer3DR3F({ frames, activations = {} }: Props) {
  const [frameIdx, setFrameIdx] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    setFrameIdx(0);
    setPlaying(false);
  }, [frames]);

  const onSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setFrameIdx(Number(e.target.value));
  }, []);

  const togglePlay = useCallback(() => setPlaying((p) => !p), []);

  return (
    <div className="flex flex-col items-center gap-3 w-full">
      <div className="w-full aspect-[3/4] rounded-2xl bg-[#0a0a0a] overflow-hidden">
        <Canvas
          camera={{ position: [0, 0, 2.2], fov: 45 }}
          dpr={[1, 2]}
          style={{ touchAction: "none" }}
        >
          <color attach="background" args={["#0a0a0a"]} />
          <ambientLight intensity={0.7} />
          <directionalLight position={[1, 2, 2]} intensity={1.2} />
          <directionalLight position={[-1, -1, -2]} intensity={0.3} />
          <Scene
            frames={frames}
            activations={activations}
            frameIdx={frameIdx}
            playing={playing}
            setFrameIdx={setFrameIdx}
          />
          <OrbitControls
            enablePan={false}
            minDistance={0.8}
            maxDistance={5}
            target={[0, 0, 0]}
          />
        </Canvas>
      </div>
      <div className="flex items-center gap-3 w-full">
        <button
          onClick={togglePlay}
          className="px-3 py-1 rounded-lg bg-[#1e1e1e] text-white text-xs hover:bg-[#2a2a2a] transition-colors flex-shrink-0"
        >
          {playing ? "⏸ 停止" : "▶ 再生"}
        </button>
        <input
          type="range"
          min={0}
          max={Math.max(0, frames.length - 1)}
          value={frameIdx}
          onChange={onSeek}
          className="flex-1 accent-red-500"
        />
        <span className="text-[#555] text-xs font-mono w-16 text-right flex-shrink-0">
          {frameIdx}/{frames.length}
        </span>
      </div>
      <p className="text-[#444] text-[10px]">
        ドラッグで回転 / ホイールorピンチでズーム（メッシュ版）
      </p>
    </div>
  );
}
