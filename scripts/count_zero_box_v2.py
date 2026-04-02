from pathlib import Path

labels_dir = Path("datasets/person_video_v2_hard/labels")
txt_files = sorted(labels_dir.glob("*.txt"))

zero_box = 0
non_zero = 0

for txt in txt_files:
    content = txt.read_text(encoding="utf-8", errors="ignore").strip()
    if content == "":
        zero_box += 1
    else:
        non_zero += 1

total = zero_box + non_zero

print(f"Total      : {total}")
print(f"Zero box   : {zero_box}")
print(f"Non-zero   : {non_zero}")
if total > 0:
    print(f"Zero ratio : {zero_box / total:.2%}")