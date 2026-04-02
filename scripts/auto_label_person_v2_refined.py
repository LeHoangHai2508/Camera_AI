from pathlib import Path
from ultralytics import YOLO

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

IMAGES_DIR = Path("datasets/person_video_v2_hard/images")
LABELS_DIR = Path("datasets/person_video_v2_hard/labels")
MODEL_PATH = r"runs\detect\models\person_bootstrap_v2\refine_v2\weights\best.pt"

IMG_SIZE = 960
CONF_THRES = 0.10

LABELS_DIR.mkdir(parents=True, exist_ok=True)
model = YOLO(MODEL_PATH)

image_files = sorted([p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMG_EXTS])

for img_path in image_files:
    results = model.predict(
        source=str(img_path),
        imgsz=IMG_SIZE,
        conf=CONF_THRES,
        classes=[0],
        device=0,
        verbose=False
    )[0]

    txt_path = LABELS_DIR / f"{img_path.stem}.txt"
    lines = []

    if results.boxes is not None and len(results.boxes) > 0:
        h, w = results.orig_shape
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            bw = x2 - x1
            bh = y2 - y1
            if bw <= 0 or bh <= 0:
                continue

            xc = x1 + bw / 2
            yc = y1 + bh / 2

            xc /= w
            yc /= h
            bw /= w
            bh /= h

            lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

    with open(txt_path, "w", encoding="utf-8") as f:
        if lines:
            f.write("\n".join(lines))

    print(f"[OK] {img_path.name} -> {len(lines)} box")

print("[XONG] auto-label refined v2 done")