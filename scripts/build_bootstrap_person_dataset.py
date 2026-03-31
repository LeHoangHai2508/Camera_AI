from pathlib import Path
import shutil
import random

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
random.seed(42)

sources = [
    ("ds1", Path("datasets/person_sources/ds1")),
    ("ds2", Path("datasets/person_sources/ds2")),
]

out_root = Path("datasets/person_bootstrap")
for sub in [
    "images/train", "images/val", "images/test",
    "labels/train", "labels/val", "labels/test"
]:
    (out_root / sub).mkdir(parents=True, exist_ok=True)

items = []

for prefix, src_root in sources:
    images_dir = src_root / "images"
    labels_dir = src_root / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        print(f"[BO QUA] Thieu images/labels: {src_root}")
        continue

    for img_path in sorted(images_dir.iterdir()):
        if img_path.suffix.lower() not in IMG_EXTS:
            continue

        txt_path = labels_dir / f"{img_path.stem}.txt"
        if not txt_path.exists():
            continue

        items.append((prefix, img_path, txt_path))

print(f"Tong so cap anh-label: {len(items)}")

random.shuffle(items)

n = len(items)
n_train = int(n * 0.8)
n_val = int(n * 0.1)

train_items = items[:n_train]
val_items = items[n_train:n_train + n_val]
test_items = items[n_train + n_val:]

splits = {
    "train": train_items,
    "val": val_items,
    "test": test_items,
}

for split, split_items in splits.items():
    for idx, (prefix, img_path, txt_path) in enumerate(split_items, start=1):
        new_stem = f"{prefix}_{idx:06d}"
        new_img = out_root / "images" / split / f"{new_stem}{img_path.suffix.lower()}"
        new_txt = out_root / "labels" / split / f"{new_stem}.txt"

        shutil.copy2(img_path, new_img)
        shutil.copy2(txt_path, new_txt)

    print(f"[OK] {split}: {len(split_items)}")

yaml_text = """path: datasets/person_bootstrap
train: images/train
val: images/val
test: images/test

names:
  0: person
"""
(out_root / "data.yaml").write_text(yaml_text, encoding="utf-8")

print("[XONG] Da tao datasets/person_bootstrap")