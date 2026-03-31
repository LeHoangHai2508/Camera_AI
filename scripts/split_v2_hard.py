from pathlib import Path
import shutil

src_images = Path("datasets/person_video/images")
src_labels = Path("datasets/person_video/labels")

dst_images = Path("datasets/person_video_v2_hard/images")
dst_labels = Path("datasets/person_video_v2_hard/labels")

dst_images.mkdir(parents=True, exist_ok=True)
dst_labels.mkdir(parents=True, exist_ok=True)

count_img = 0
count_lbl = 0

for p in src_images.iterdir():
    if p.is_file() and p.name.startswith("v2_"):
        shutil.move(str(p), str(dst_images / p.name))
        count_img += 1

for p in src_labels.iterdir():
    if p.is_file() and p.name.startswith("v2_"):
        shutil.move(str(p), str(dst_labels / p.name))
        count_lbl += 1

print(f"[XONG] moved images = {count_img}, labels = {count_lbl}")