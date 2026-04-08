"""
roi_tool.py — Interactive ROI polygon selection tool.

Opens a frame image in an OpenCV window. Click to add polygon points.
Supports multiple worker and buffer ROIs.

Controls:
    Left-click  — add a point to current polygon
    'n'         — finish current polygon, start next one
    'u'         — undo last point
    's'         — save all ROIs to JSON and exit
    'q' / ESC   — quit without saving
    'r'         — reset all polygons

Usage:
    python src/roi_tool.py --frame assets/frames_person/frame_000000.jpg \
                           --output configs/roi_cam01.json \
                           --camera_id cam01
"""

import argparse
import json
import os
import cv2
import numpy as np

import sys
sys.path.insert(0, os.path.dirname(__file__))
from utils.common import COLOR_GREEN, COLOR_YELLOW, COLOR_CYAN, COLOR_RED, ensure_dir


class ROISelector:
    """Interactive polygon ROI selector using OpenCV."""

    def __init__(self, frame: np.ndarray):
        self.original = frame.copy()
        self.frame = frame.copy()
        self.current_points = []
        self.worker_rois = []
        self.buffer_rois = []
        self.mode = "worker"  # "worker" or "buffer"
        self.roi_counter = {"worker": 0, "buffer": 0}

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append([x, y])
            self._redraw()

    def _redraw(self):
        """Redraw frame with all ROIs and current polygon."""
        self.frame = self.original.copy()

        # Draw saved worker ROIs
        for roi in self.worker_rois:
            pts = np.array(roi["points"], dtype=np.int32)
            cv2.polylines(self.frame, [pts], True, COLOR_GREEN, 2)
            cv2.putText(self.frame, roi["id"], tuple(pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_GREEN, 2)

        # Draw saved buffer ROIs
        for roi in self.buffer_rois:
            pts = np.array(roi["points"], dtype=np.int32)
            cv2.polylines(self.frame, [pts], True, COLOR_YELLOW, 2)
            cv2.putText(self.frame, roi["id"], tuple(pts[0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_YELLOW, 2)

        # Draw current polygon in progress
        color = COLOR_GREEN if self.mode == "worker" else COLOR_YELLOW
        if len(self.current_points) > 0:
            for pt in self.current_points:
                cv2.circle(self.frame, tuple(pt), 5, color, -1)
            if len(self.current_points) > 1:
                pts = np.array(self.current_points, dtype=np.int32)
                cv2.polylines(self.frame, [pts], False, color, 2)

        # Status bar
        status = (f"Mode: {self.mode.upper()} ROI | "
                  f"Points: {len(self.current_points)} | "
                  f"Workers: {len(self.worker_rois)} | "
                  f"Buffers: {len(self.buffer_rois)}")
        h = self.frame.shape[0]
        cv2.putText(self.frame, status, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_CYAN, 1)

        help_text = "[n]ext ROI  [u]ndo  [m]ode  [s]ave  [r]eset  [q]uit"
        cv2.putText(self.frame, help_text, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    def finish_current_roi(self):
        """Save current polygon and start a new one."""
        if len(self.current_points) < 3:
            print("Need at least 3 points for a polygon. Skipping.")
            return

        self.roi_counter[self.mode] += 1
        roi_id = f"{self.mode}_{self.roi_counter[self.mode]:02d}"

        roi_entry = {
            "id": roi_id,
            "points": self.current_points.copy()
        }

        if self.mode == "worker":
            self.worker_rois.append(roi_entry)
        else:
            self.buffer_rois.append(roi_entry)

        print(f"Saved {self.mode} ROI: {roi_id} "
              f"({len(self.current_points)} points)")
        self.current_points = []
        self._redraw()

    def toggle_mode(self):
        """Switch between worker and buffer mode."""
        self.mode = "buffer" if self.mode == "worker" else "worker"
        print(f"Switched to {self.mode.upper()} mode")
        self._redraw()

    def undo_point(self):
        """Remove last added point."""
        if self.current_points:
            self.current_points.pop()
            self._redraw()

    def reset_all(self):
        """Clear everything."""
        self.current_points = []
        self.worker_rois = []
        self.buffer_rois = []
        self.roi_counter = {"worker": 0, "buffer": 0}
        self._redraw()

    def to_json(self, camera_id: str, video_path: str = "") -> dict:
        """Build the JSON config dict."""
        return {
            "camera_id": camera_id,
            "video_path": video_path,
            "worker_rois": self.worker_rois,
            "buffer_rois": self.buffer_rois,
        }


def run_roi_tool(frame_path: str, output_path: str,
                 camera_id: str = "cam01",
                 video_path: str = ""):
    """Open interactive ROI selector window."""
    frame = cv2.imread(frame_path)
    if frame is None:
        raise RuntimeError(f"Cannot load image: {frame_path}")

    selector = ROISelector(frame)
    win_name = "ROI Selector — AI Camera"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win_name, selector.mouse_callback)
    selector._redraw()

    print("\n=== ROI Tool ===")
    print("Left-click to add points. See keyboard shortcuts on image.\n")

    while True:
        cv2.imshow(win_name, selector.frame)
        key = cv2.waitKey(20) & 0xFF

        if key == ord('q') or key == 27:  # quit
            print("Quit without saving.")
            break
        elif key == ord('n'):  # next ROI
            selector.finish_current_roi()
        elif key == ord('m'):  # toggle mode
            selector.toggle_mode()
        elif key == ord('u'):  # undo
            selector.undo_point()
        elif key == ord('r'):  # reset
            selector.reset_all()
            print("Reset all ROIs.")
        elif key == ord('s'):  # save
            # Finish current polygon if any
            if len(selector.current_points) >= 3:
                selector.finish_current_roi()

            config = selector.to_json(camera_id, video_path)
            ensure_dir(os.path.dirname(output_path) or ".")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"\nSaved ROI config → {output_path}")
            print(f"  Worker ROIs: {len(selector.worker_rois)}")
            print(f"  Buffer ROIs: {len(selector.buffer_rois)}")
            break

    cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(
        description="Interactive ROI polygon selection tool"
    )
    parser.add_argument("--frame", required=True,
                        help="Path to a representative frame image")
    parser.add_argument("--output", default="configs/roi_cam01.json",
                        help="Output JSON path (default: configs/roi_cam01.json)")
    parser.add_argument("--camera_id", default="cam01",
                        help="Camera ID (default: cam01)")
    parser.add_argument("--video_path", default="",
                        help="Video path to store in config")
    args = parser.parse_args()

    run_roi_tool(args.frame, args.output, args.camera_id, args.video_path)


if __name__ == "__main__":
    main()
