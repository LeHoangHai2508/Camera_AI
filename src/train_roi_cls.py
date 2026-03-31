"""
train_roi_cls.py — Train YOLO26-cls ROI state classification model.

Dataset structure expected:
    datasets/roi_state/
    ├── train/
    │   ├── empty/
    │   ├── normal/
    │   ├── full/
    │   └── overload/
    ├── val/
    └── test/

Usage:
    python src/train_roi_cls.py --data datasets/roi_state \
                                --model yolo26n-cls.pt \
                                --epochs 50 \
                                --imgsz 224 \
                                --batch 16 \
                                --device 0
"""

import argparse
from pathlib import Path


def train_roi_classifier(data: str, model: str = "yolo26n-cls.pt",
                         epochs: int = 50, imgsz: int = 224,
                         batch: int = 16, device: str = "0",
                         project: str = "models/roi_state",
                         name: str = "train"):
    """Train ROI state classification model using Ultralytics YOLO-cls."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  ROI State Classification — Training")
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

    # Copy best weights
    best_src = Path(project) / name / "weights" / "best.pt"
    best_dst = Path(project) / "best_roi_cls.pt"
    if best_src.exists():
        import shutil
        shutil.copy2(best_src, best_dst)
        print(f"\nBest weights saved → {best_dst}")

    print("\nTraining complete!")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Train YOLO26-cls ROI state classification model"
    )
    parser.add_argument("--data", default="datasets/roi_state",
                        help="Path to classification dataset root")
    parser.add_argument("--model", default="yolo26n-cls.pt",
                        help="Pretrained model (default: yolo26n-cls.pt)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=224)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0",
                        help="Device: 0, 1, cpu")
    parser.add_argument("--project", default="models/roi_state")
    parser.add_argument("--name", default="train")
    args = parser.parse_args()

    train_roi_classifier(
        data=args.data, model=args.model,
        epochs=args.epochs, imgsz=args.imgsz,
        batch=args.batch, device=args.device,
        project=args.project, name=args.name,
    )


if __name__ == "__main__":
    main()
