"""
train_roi_cls.py

Train YOLO26 classification model for ROI state classification.

Expected dataset structure:
    datasets/roi_state/
    ├── train/
    │   ├── empty/
    │   ├── normal/
    │   ├── full/
    │   └── overload/
    ├── val/
    │   ├── empty/
    │   ├── normal/
    │   ├── full/
    │   └── overload/
    └── test/
        ├── empty/
        ├── normal/
        ├── full/
        └── overload/

Usage:
    python src/train_roi_cls.py --data datasets/roi_state --model yolo26n-cls.pt --epochs 50 --imgsz 224 --batch 16 --device 0
    python src/train_roi_cls.py --data datasets/roi_state --model yolo26n-cls.pt --epochs 30 --imgsz 224 --batch 8 --device cpu
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def count_images_in_dir(folder: Path) -> int:
    return sum(1 for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS)


def get_class_dirs(split_dir: Path) -> List[Path]:
    if not split_dir.exists():
        return []
    return sorted([p for p in split_dir.iterdir() if p.is_dir()])


def summarize_split(split_dir: Path) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for class_dir in get_class_dirs(split_dir):
        summary[class_dir.name] = count_images_in_dir(class_dir)
    return summary


def validate_dataset_root(data_root: Path) -> Tuple[List[str], Dict[str, Dict[str, int]]]:
    if not data_root.exists():
        raise FileNotFoundError(f"Không tìm thấy dataset root: {data_root}")

    train_dir = data_root / "train"
    val_dir = data_root / "val"
    test_dir = data_root / "test"

    if not train_dir.exists():
        raise FileNotFoundError(f"Thiếu thư mục train: {train_dir}")
    if not val_dir.exists():
        raise FileNotFoundError(f"Thiếu thư mục val: {val_dir}")

    train_summary = summarize_split(train_dir)
    val_summary = summarize_split(val_dir)
    test_summary = summarize_split(test_dir) if test_dir.exists() else {}

    if not train_summary:
        raise ValueError(f"train không có class folder nào: {train_dir}")
    if not val_summary:
        raise ValueError(f"val không có class folder nào: {val_dir}")

    train_classes = set(train_summary.keys())
    val_classes = set(val_summary.keys())

    if train_classes != val_classes:
        raise ValueError(
            "Class giữa train và val không khớp.\n"
            f"train: {sorted(train_classes)}\n"
            f"val:   {sorted(val_classes)}"
        )

    if test_dir.exists():
        test_classes = set(test_summary.keys())
        if test_classes != train_classes:
            print("[CANH BAO] Class giữa test và train không khớp.")
            print(f"train: {sorted(train_classes)}")
            print(f"test:  {sorted(test_classes)}")

    for class_name, n_imgs in train_summary.items():
        if n_imgs == 0:
            raise ValueError(f"Class train/{class_name} không có ảnh")
    for class_name, n_imgs in val_summary.items():
        if n_imgs == 0:
            raise ValueError(f"Class val/{class_name} không có ảnh")

    summaries = {
        "train": train_summary,
        "val": val_summary,
        "test": test_summary,
    }
    return sorted(train_classes), summaries


def print_dataset_summary(data_root: Path, class_names: List[str], summaries: Dict[str, Dict[str, int]]) -> None:
    print("=" * 70)
    print("DATASET SUMMARY")
    print("=" * 70)
    print(f"Root: {data_root}")
    print(f"Classes: {class_names}")
    print("-" * 70)

    for split_name in ["train", "val", "test"]:
        split_summary = summaries.get(split_name, {})
        if not split_summary:
            if split_name == "test":
                print("test : không có hoặc chưa dùng")
                print("-" * 70)
                continue
        total = sum(split_summary.values())
        print(f"{split_name}: tổng {total} ảnh")
        for cls in class_names:
            n = split_summary.get(cls, 0)
            print(f"  - {cls:<10}: {n}")
        print("-" * 70)


def normalize_device(device: str):
    device = str(device).strip().lower()
    return int(device) if device.isdigit() else device


def copy_best_weights(project: Path, name: str, results_obj=None) -> Path | None:
    candidates: List[Path] = []

    if results_obj is not None:
        save_dir = getattr(results_obj, "save_dir", None)
        if save_dir is not None:
            candidates.append(Path(save_dir) / "weights" / "best.pt")
            candidates.append(Path(save_dir) / "best.pt")

    candidates.append(project / name / "weights" / "best.pt")
    candidates.append(project / name / "best.pt")

    best_src = None
    for p in candidates:
        if p.exists():
            best_src = p
            break

    if best_src is None:
        return None

    best_dst = project / "best_roi_cls.pt"
    project.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_src, best_dst)
    return best_dst


def train_roi_classifier(
    data: str,
    model: str = "yolo26n-cls.pt",
    epochs: int = 50,
    imgsz: int = 224,
    batch: int = 16,
    device: str = "0",
    project: str = "models/roi_state",
    name: str = "train",
    workers: int = 4,
    patience: int = 20,
    seed: int = 42,
    exist_ok: bool = True,
):
    from ultralytics import YOLO

    data_root = Path(data)
    project_dir = Path(project)

    class_names, summaries = validate_dataset_root(data_root)
    print_dataset_summary(data_root, class_names, summaries)

    print("=" * 70)
    print("ROI STATE CLASSIFICATION TRAINING")
    print("=" * 70)
    print(f"Model    : {model}")
    print(f"Data     : {data_root}")
    print(f"Epochs   : {epochs}")
    print(f"ImgSz    : {imgsz}")
    print(f"Batch    : {batch}")
    print(f"Device   : {device}")
    print(f"Project  : {project_dir}")
    print(f"Name     : {name}")
    print(f"Workers  : {workers}")
    print(f"Patience : {patience}")
    print(f"Seed     : {seed}")
    print("=" * 70)

    yolo = YOLO(model)

    results = yolo.train(
        data=str(data_root),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=normalize_device(device),
        project=str(project_dir),
        name=name,
        exist_ok=exist_ok,
        workers=workers,
        patience=patience,
        seed=seed,
        verbose=True,
    )

    best_dst = copy_best_weights(project_dir, name, results)

    print("\n" + "=" * 70)
    if best_dst is not None and best_dst.exists():
        print(f"Best weights saved -> {best_dst}")
    else:
        print("Không tìm thấy best.pt để copy về best_roi_cls.pt")
    print("Training complete.")
    print("=" * 70)

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train YOLO26 classification model for ROI state classification"
    )
    parser.add_argument(
        "--data",
        default="datasets/roi_state",
        help="Path to classification dataset root",
    )
    parser.add_argument(
        "--model",
        default="yolo26n-cls.pt",
        help="Pretrained classification model",
    )
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=224, help="Image size")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument(
        "--device",
        default="0",
        help="Training device: 0, 1, cpu",
    )
    parser.add_argument(
        "--project",
        default="models/roi_state",
        help="Directory to save training runs",
    )
    parser.add_argument(
        "--name",
        default="train",
        help="Run name inside project directory",
    )
    parser.add_argument("--workers", type=int, default=4, help="Dataloader workers")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping patience")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--exist-ok",
        action="store_true",
        help="Allow overwriting existing run directory",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    train_roi_classifier(
        data=args.data,
        model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        workers=args.workers,
        patience=args.patience,
        seed=args.seed,
        exist_ok=args.exist_ok,
    )


if __name__ == "__main__":
    main()