from pathlib import Path
import random
import cv2

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

images_dir = Path("datasets/person_video_v2_hard/images")
labels_dir = Path("datasets/person_video_v2_hard/labels")
out_dir = Path("datasets/person_video_v2_hard/preview")
out_dir.mkdir(parents=True, exist_ok=True)

image_files = [p for p in images_dir.iterdir() if p.suffix.lower() in IMG_EXTS]
sample_files = random.sample(image_files, min(50, len(image_files)))

for img_path in sample_files:
    img = cv2.imread(str(img_path))
    if img is None:
        continue

    h, w = img.shape[:2]
    txt_path = labels_dir / f"{img_path.stem}.txt"

    if txt_path.exists():
        content = txt_path.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            for line in content.splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue

                _, xc, yc, bw, bh = parts
                xc, yc, bw, bh = map(float, [xc, yc, bw, bh])

                x1 = int((xc - bw / 2) * w)
                y1 = int((yc - bh / 2) * h)
                x2 = int((xc + bw / 2) * w)
                y2 = int((yc + bh / 2) * h)

                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imwrite(str(out_dir / img_path.name), img)

print("[XONG] preview saved")