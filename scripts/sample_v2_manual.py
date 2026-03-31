from pathlib import Path
import shutil

src = Path("datasets/person_video_v2_hard/images")
dst = Path("datasets/person_video_v2_manual/images")
dst.mkdir(parents=True, exist_ok=True)

files = sorted([p for p in src.iterdir() if p.is_file() and p.name.startswith("v2_")])

# lấy mỗi 2 frame 1 ảnh cho đến khi đủ 150
selected = files[::2][:150]

for p in selected:
    shutil.copy2(p, dst / p.name)

print(f"[XONG] copied {len(selected)} images to manual set")