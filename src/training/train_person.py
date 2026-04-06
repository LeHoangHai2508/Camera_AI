"""
train_person.py — Train YOLO26 person detection model.

Usage:
    python src/train_person.py --data datasets/person/data.yaml \
                               --model yolo26n.pt \
                               --epochs 50 \
                               --imgsz 640 \
                               --batch 8 \
                               --device 0
"""

import argparse
import os
from pathlib import Path


def train_person(data: str, model: str = "yolo26n.pt",
                 epochs: int = 50, imgsz: int = 640,
                 batch: int = 8, device: str = "0",
                 project: str = "models/person",
                 name: str = "train"):
    """Train person detection model using Ultralytics YOLO."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  Person Detection — Training")
    print("=" * 60)
    print(f"  Model:   {model}")
    print(f"  Data:    {data}")
    print(f"  Epochs:  {epochs}")
    print(f"  ImgSz:   {imgsz}")
    print(f"  Batch:   {batch}")
    print(f"  Device:  {device}")
    print(f"  Project: {project}")
    print("=" * 60)

    yolo = YOLO(model)

    results = yolo.train(
        data=data,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=int(device) if device.isdigit() else device,
        project=project,
        name=name,
        exist_ok=True,
        verbose=True,
    )

    # Copy best weights to a convenient location
    best_src = Path(project) / name / "weights" / "best.pt"
    best_dst = Path(project) / "best_person.pt"
    if best_src.exists():
        import shutil
        shutil.copy2(best_src, best_dst)
        print(f"\nBest weights saved → {best_dst}")

    print("\nTraining complete!")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLO26 person detection model"
    )
    parser.add_argument("--data", default="datasets/person/data.yaml",
                        help="Path to dataset YAML")
    parser.add_argument("--model", default="yolo26n.pt",
                        help="Pretrained model (default: yolo26n.pt)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0",
                        help="Device: 0, 1, cpu")
    parser.add_argument("--project", default="models/person",
                        help="Output project directory")
    parser.add_argument("--name", default="train",
                        help="Run name inside project dir")
    args = parser.parse_args()

    train_person(
        data=args.data, model=args.model,
        epochs=args.epochs, imgsz=args.imgsz,
        batch=args.batch, device=args.device,
        project=args.project, name=args.name,
    )


if __name__ == "__main__":
    main()
