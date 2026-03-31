from pathlib import Path
import shutil

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

sources = [
    ("v1", Path("assets/frames_person/video1")),
    ("v2", Path("assets/frames_person/video2")),
    ("v3", Path("assets/frames_person/video3")),
]

dst = Path("datasets/person_video/images")
dst.mkdir(parents=True, exist_ok=True)

for prefix, src in sources:
    if not src.exists():
        print(f"[BO QUA] Khong tim thay thu muc: {src}")
        continue

    files = sorted([p for p in src.iterdir() if p.suffix.lower() in IMG_EXTS])

    for idx, file_path in enumerate(files, start=1):
        new_name = f"{prefix}_{idx:06d}{file_path.suffix.lower()}"
        shutil.copy2(file_path, dst / new_name)

    print(f"[OK] {prefix}: da copy {len(files)} anh")

print("[XONG] Da gop frame vao datasets/person_video/images")