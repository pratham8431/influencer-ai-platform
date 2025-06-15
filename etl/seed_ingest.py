#!/usr/bin/env python3
import yaml, sys
from pathlib import Path
from etl.youtube_scraper import load_to_db

def main(config_path: str):
    cfg = yaml.safe_load(Path(config_path).read_text())
    for vertical, seeds in cfg["verticals"].items():
        print(f"\n▶️  Processing vertical: {vertical}")
        for method in ("channel", "video"):
            for seed in seeds:
                print(f"  • {method.upper()} “{seed}” …", end=" ")
                load_to_db(seed, max_results=20, method=method)
                print("Done.")

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else "config/verticals.yaml"
    main(cfg)
