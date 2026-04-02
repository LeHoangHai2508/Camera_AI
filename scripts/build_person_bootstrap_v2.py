from pathlib import Path
import shutil
import random

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
random.seed(42)

sources = [
    ("ds1", Path("datasets/person_sources/ds1")),
    ("ds2", Path("datasets/person_sources/ds2")),
    ("v2m", Path("datasets/person_video_v2_manual")),
]

out_root = Path("datasets/person_bootstrap_v2")
for sub in [
    "images/train", "images/val", "images/test",
    "labels/train", "labels/val", "labels/test"
]:
    (out_root / sub).mkdir(parents=True, exist_ok=True)

items = []

for prefix, src_root in sources:
    images_dir = src_root / "images"
    labels_dir = src_root / "labels"

    for img_path in sorted(images_dir.iterdir()):
        if img_path.suffix.lower() not in IMG_EXTS:
            continue
        txt_path = labels_dir / f"{img_path.stem}.txt"
        if txt_path.exists():
            items.append((prefix, img_path, txt_path))

random.shuffle(items)

n = len(items)
n_train = int(n * 0.8)
n_val = int(n * 0.1)

splits = {
    "train": items[:n_train],
    "val": items[n_train:n_train+n_val],
    "test": items[n_train+n_val:]
}

for split, split_items in splits.items():
    for idx, (prefix, img_path, txt_path) in enumerate(split_items, start=1):
        new_stem = f"{prefix}_{idx:06d}"
        shutil.copy2(img_path, out_root / "images" / split / f"{new_stem}{img_path.suffix.lower()}")
        shutil.copy2(txt_path, out_root / "labels" / split / f"{new_stem}.txt")

yaml_text = """path: datasets/person_bootstrap_v2
train: images/train
val: images/val
test: images/test

names:
  0: person
"""
(out_root / "data.yaml").write_text(yaml_text, encoding="utf-8")

print("[XONG] built datasets/person_bootstrap_v2")