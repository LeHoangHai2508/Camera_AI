from pathlib import Path
from ultralytics import YOLO
import cv2

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# ====== Cấu hình ======
IMAGES_DIR = Path("datasets/person_video/images")
LABELS_DIR = Path("datasets/person_video/labels")
MODEL_PATH = r"runs\detect\models\person_bootstrap\bootstrap\weights\best.pt"   # có thể thay bằng weight person khác nếu bạn có
CONF_THRES = 0.20
PERSON_CLASS_ID_COCO = 0    # trong COCO, person = 0
# ======================

LABELS_DIR.mkdir(parents=True, exist_ok=True)

model = YOLO(MODEL_PATH)

image_files = sorted([p for p in IMAGES_DIR.iterdir() if p.suffix.lower() in IMG_EXTS])

for img_path in image_files:
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"[BO QUA] Khong doc duoc anh: {img_path}")
        continue

    h, w = img.shape[:2]
    results = model.predict(
    source=str(img_path),
    imgsz=960,
    conf=0.12,
    classes=[0],
    device=0,
    verbose=False
)[0]

    txt_path = LABELS_DIR / f"{img_path.stem}.txt"

    lines = []

    if results.boxes is not None:
        for box in results.boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())

            if cls_id != PERSON_CLASS_ID_COCO:
                continue
            if conf < CONF_THRES:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))

            bw = x2 - x1
            bh = y2 - y1
            xc = x1 + bw / 2
            yc = y1 + bh / 2

            # chuẩn hóa YOLO
            xc /= w
            yc /= h
            bw /= w
            bh /= h

            if bw <= 0 or bh <= 0:
                continue

            lines.append(f"0 {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}")

    with open(txt_path, "w", encoding="utf-8") as f:
        if lines:
            f.write("\n".join(lines))

    print(f"[OK] {img_path.name} -> {len(lines)} box")

print("[XONG] Da auto-label xong datasets/person_video")