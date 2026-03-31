from pathlib import Path
import sys

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

def is_float(x: str) -> bool:
    try:
        float(x)
        return True
    except:
        return False

def check_dataset(root_dir: str):
    root = Path(root_dir)
    images_dir = root / "images"
    labels_dir = root / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        print(f"[LOI] Khong tim thay images/ hoac labels/ trong: {root}")
        return

    image_files = sorted([p for p in images_dir.iterdir() if p.suffix.lower() in IMG_EXTS])
    label_files = sorted([p for p in labels_dir.iterdir() if p.suffix.lower() == ".txt"])

    image_stems = {p.stem for p in image_files}
    label_stems = {p.stem for p in label_files}

    missing_labels = sorted(image_stems - label_stems)
    missing_images = sorted(label_stems - image_stems)

    empty_labels = []
    bad_format = []
    bad_class_ids = []
    bad_ranges = []

    for txt_file in label_files:
        content = txt_file.read_text(encoding="utf-8", errors="ignore").strip()

        if content == "":
            empty_labels.append(txt_file.name)
            continue

        lines = content.splitlines()
        for i, line in enumerate(lines, start=1):
            parts = line.strip().split()

            if len(parts) != 5:
                bad_format.append((txt_file.name, i, line))
                continue

            cls_id, xc, yc, w, h = parts

            if not cls_id.isdigit():
                bad_format.append((txt_file.name, i, line))
                continue

            if not all(is_float(v) for v in [xc, yc, w, h]):
                bad_format.append((txt_file.name, i, line))
                continue

            cls_id = int(cls_id)
            xc, yc, w, h = map(float, [xc, yc, w, h])

            if cls_id != 0:
                bad_class_ids.append((txt_file.name, i, cls_id))

            if not (0 <= xc <= 1 and 0 <= yc <= 1 and 0 < w <= 1 and 0 < h <= 1):
                bad_ranges.append((txt_file.name, i, (xc, yc, w, h)))

    print("=" * 70)
    print(f"DATASET: {root}")
    print(f"So anh: {len(image_files)}")
    print(f"So label txt: {len(label_files)}")
    print(f"Anh thieu label: {len(missing_labels)}")
    print(f"Label thieu anh: {len(missing_images)}")
    print(f"Label rong (0 object): {len(empty_labels)}")
    print(f"Dong sai format: {len(bad_format)}")
    print(f"Class ID khac 0: {len(bad_class_ids)}")
    print(f"Toa do YOLO sai mien gia tri: {len(bad_ranges)}")

    def preview(title, items, limit=10):
        if items:
            print(f"\n{title}:")
            for x in items[:limit]:
                print(" -", x)

    preview("Mot so anh thieu label", missing_labels)
    preview("Mot so label thieu anh", missing_images)
    preview("Mot so label rong", empty_labels)
    preview("Mot so dong sai format", bad_format)
    preview("Mot so class id khac 0", bad_class_ids)
    preview("Mot so toa do sai", bad_ranges)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Cach dung:")
        print(r'python scripts\check_yolo_dataset.py "D:\duong_dan_dataset"')
        sys.exit(1)

    check_dataset(sys.argv[1])