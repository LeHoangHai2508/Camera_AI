"""
extract_frames.py — Extract frames from video at regular intervals.

Usage:
    python src/extract_frames.py --video assets/videos/video1.mp4 \
                                 --output_dir assets/frames_person \
                                 --interval_sec 1.0
"""

import argparse
import os
import cv2
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(__file__))
from utils.common import ensure_dir


def extract_frames(video_path: str, out_dir: str,
                   interval_sec: float = 1.0):
    """
    Extract frames from a video file at every `interval_sec` seconds.

    Saved as:  {video_stem}_{frame_idx:06d}_{time_sec:.1f}s.jpg
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_stem = Path(video_path).stem

    ensure_dir(out_dir)

    frame_interval = max(1, int(fps * interval_sec))
    saved = 0
    frame_idx = 0

    print(f"Video: {video_path}")
    print(f"FPS: {fps:.1f} | Total frames: {total_frames}")
    print(f"Extracting every {interval_sec}s ({frame_interval} frames)")
    print(f"Output: {out_dir}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            time_sec = frame_idx / fps
            filename = f"{video_stem}_{frame_idx:06d}_{time_sec:.1f}s.jpg"
            save_path = os.path.join(out_dir, filename)
            cv2.imwrite(save_path, frame)
            saved += 1

        frame_idx += 1

    cap.release()
    print(f"Done. Saved {saved} frames.")
    return saved


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from video at regular intervals"
    )
    parser.add_argument("--video", required=True,
                        help="Path to input video")
    parser.add_argument("--output_dir", required=True,
                        help="Directory to save extracted frames")
    parser.add_argument("--interval_sec", type=float, default=1.0,
                        help="Interval in seconds between frames (default: 1.0)")
    args = parser.parse_args()

    extract_frames(args.video, args.output_dir, args.interval_sec)


if __name__ == "__main__":
    main()
