"""
crop_roi.py — Crop buffer ROI regions from frames for classification labeling.

Reads frames from a directory, applies the ROI mask from config,
crops each buffer ROI, and saves the crops for manual labeling.

Usage:
    python src/crop_roi.py --frames_dir assets/frames_person \
                           --roi_config configs/roi_cam01.json \
                           --output_dir assets/roi_crops
"""

import argparse
import os
import cv2
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(__file__))
from common import ensure_dir
from config_utils import load_roi_config, get_roi_points


def crop_polygon_region(frame: np.ndarray,
                        points: list) -> np.ndarray:
    """
    Crop the bounding rect of a polygon region from a frame,
    with pixels outside the polygon set to black.
    """
    pts = np.array(points, dtype=np.int32)

    # Bounding rectangle
    x, y, w, h = cv2.boundingRect(pts)

    # Create mask
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)

    # Apply mask
    masked = cv2.bitwise_and(frame, frame, mask=mask)

    # Crop to bounding rect
    cropped = masked[y:y+h, x:x+w]
    return cropped


def save_roi_crops(frames_dir: str, roi_config_path: str,
                   output_dir: str):
    """
    For every frame in `frames_dir`, crop each buffer ROI
    and save to `output_dir/{roi_id}/`.
    """
    cfg = load_roi_config(roi_config_path)
    buffer_rois = cfg.get("buffer_rois", [])

    if not buffer_rois:
        print("No buffer ROIs found in config.")
        return

    # Gather frame files
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    frame_files = sorted([
        f for f in os.listdir(frames_dir)
        if Path(f).suffix.lower() in exts
    ])

    if not frame_files:
        print(f"No image files found in {frames_dir}")
        return

    print(f"Found {len(frame_files)} frames, "
          f"{len(buffer_rois)} buffer ROIs")

    total_saved = 0
    for roi in buffer_rois:
        roi_id = roi["id"]
        points = get_roi_points(roi)
        roi_out = os.path.join(output_dir, roi_id)
        ensure_dir(roi_out)

        for fname in frame_files:
            fpath = os.path.join(frames_dir, fname)
            frame = cv2.imread(fpath)
            if frame is None:
                continue

            crop = crop_polygon_region(frame, points)
            if crop.size == 0:
                continue

            stem = Path(fname).stem
            save_path = os.path.join(roi_out, f"{stem}_{roi_id}.jpg")
            cv2.imwrite(save_path, crop)
            total_saved += 1

    print(f"Done. Saved {total_saved} ROI crops to {output_dir}")
    print("\nNext step: manually sort crops into class folders:")
    print("  empty / normal / full / overload")


def main():
    parser = argparse.ArgumentParser(
        description="Crop buffer ROI regions from frames"
    )
    parser.add_argument("--frames_dir", required=True,
                        help="Directory containing extracted frames")
    parser.add_argument("--roi_config", required=True,
                        help="ROI JSON config file")
    parser.add_argument("--output_dir", default="assets/roi_crops",
                        help="Output directory for crops")
    args = parser.parse_args()

    save_roi_crops(args.frames_dir, args.roi_config, args.output_dir)


if __name__ == "__main__":
    main()
