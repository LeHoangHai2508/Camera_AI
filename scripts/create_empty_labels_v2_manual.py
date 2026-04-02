from pathlib import Path

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

images_dir = Path("datasets/person_video_v2_manual/images")
labels_dir = Path("datasets/person_video_v2_manual/labels")
labels_dir.mkdir(parents=True, exist_ok=True)

count_created = 0

for img_file in images_dir.iterdir():
    if img_file.suffix.lower() not in IMG_EXTS:
        continue
    txt_file = labels_dir / f"{img_file.stem}.txt"
    if not txt_file.exists():
        txt_file.touch()
        count_created += 1

print(f"[XONG] created {count_created} empty labels")