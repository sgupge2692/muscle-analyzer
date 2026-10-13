"""
使い方:
  python visualize_muscles.py --input data/processed/muscle_activation.json --rep 1
  python visualize_muscles.py --input data/processed/muscle_activation.json --all
"""
import sys, json, argparse
from pathlib import Path
sys.path.append("src")
from visualization.heatmap_renderer import render

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input",  "-i", default="data/processed/muscle_activation.json")
    p.add_argument("--rep",    "-r", type=int, default=1)
    p.add_argument("--all",    "-a", action="store_true")
    p.add_argument("--output", "-o", default=None)
    args = p.parse_args()

    data = json.loads(Path(args.input).read_text())
    targets = list(data.keys()) if args.all else [f"rep_{args.rep}"]

    for key in targets:
        if key not in data:
            print(f"❌ {key} が見つかりません。キー: {list(data.keys())}")
            sys.exit(1)
        n   = key.split("_")[-1]
        out = args.output if (args.output and len(targets)==1) else f"output/heatmap_{key}.html"
        render(data[key], f"スクワット {key} 筋肉活動", out)
        print(f"  → open {out}")

if __name__ == "__main__":
    main()
