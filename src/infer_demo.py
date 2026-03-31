"""
infer_demo.py — Full AI Camera inference pipeline.

Reads video → detects persons → tracks → checks worker ROI →
crops buffer ROI → classifies state → smooths → applies rules →
draws overlay → writes output video + logs + snapshots.

Usage:
    python src/infer_demo.py \
        --video assets/videos/video1.mp4 \
        --roi configs/roi_cam01.json \
        --rules configs/rules.yaml \
        --person_model models/person/best_person.pt \
        --roi_cls_model models/roi_state/best_roi_cls.pt \
        --output outputs/videos/demo_output.mp4
"""

import argparse
import os
import sys
import time
import cv2
import numpy as np
import torch
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from common import (
    ensure_dir, frame_to_sec, sec_to_mmss,
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_CYAN,
)
from config_utils import load_roi_config, load_rules, load_runtime
from tracker_utils import (
    StateSmoother, PresenceTracker, filter_persons_in_roi,
)
from rule_engine import WorkerAbsenceRule, BacklogRule
from event_logger import EventLogger
from draw_utils import (
    draw_polygon, draw_person_bbox, draw_roi_state,
    draw_timer, draw_alert_banner, draw_info_panel,
)


def crop_polygon_region_for_cls(frame, points):
    """Crop polygon bounding rect from frame."""
    pts = np.array(points, dtype=np.int32)
    x, y, w, h = cv2.boundingRect(pts)

    # Clamp to frame bounds
    fh, fw = frame.shape[:2]
    x, y = max(0, x), max(0, y)
    w = min(w, fw - x)
    h = min(h, fh - y)

    if w <= 0 or h <= 0:
        return None

    cropped = frame[y:y+h, x:x+w].copy()
    return cropped


def run_pipeline(video_path: str, roi_path: str, rules_path: str,
                 person_model_path: str, roi_cls_model_path: str,
                 output_path: str, runtime_path: str = None,
                 tracker_cfg: str = "bytetrack.yaml",
                 show_preview: bool = False,
                 device: str = "auto"):
    """Main inference pipeline."""

    # ── Load configs ──────────────────────────────────────
    roi_cfg = load_roi_config(roi_path)
    rules_cfg = load_rules(rules_path)

    # Runtime defaults
    process_fps = 5
    imgsz_detect = 640
    imgsz_cls = 224
    conf_detect = 0.45
    conf_cls = 0.40
    smooth_window = 10
    snapshot_on_alert = True

    if runtime_path and os.path.exists(runtime_path):
        rt = load_runtime(runtime_path)
        process_fps = rt.get("process_fps", process_fps)
        imgsz_detect = rt.get("imgsz_detect", imgsz_detect)
        imgsz_cls = rt.get("imgsz_classify", imgsz_cls)
        conf_detect = rt.get("confidence_detect", conf_detect)
        conf_cls = rt.get("confidence_classify", conf_cls)
        smooth_window = rt.get("smoothing_window", smooth_window)
        tracker_cfg = rt.get("tracker", tracker_cfg)
        snapshot_on_alert = rt.get("snapshot_on_alert", snapshot_on_alert)

    camera_id = roi_cfg.get("camera_id", "cam01")
    worker_rois = roi_cfg.get("worker_rois", [])
    buffer_rois = roi_cfg.get("buffer_rois", [])

    # Rule thresholds
    wa_cfg = rules_cfg.get("worker_absence", {})
    bl_cfg = rules_cfg.get("backlog_alert", {})
    t_absent = wa_cfg.get("threshold_sec", 15)
    grace = wa_cfg.get("grace_frames", 3)
    t_backlog = bl_cfg.get("threshold_sec", 20)
    trigger_states = bl_cfg.get("trigger_states", ["full", "overload"])

    # ── Resolve device ────────────────────────────────────
    if device == "auto":
        if torch.cuda.is_available():
            device = "0"  # First GPU
        else:
            device = "cpu"

    use_gpu = device != "cpu"
    device_name = (torch.cuda.get_device_name(int(device))
                   if use_gpu and torch.cuda.is_available()
                   else "CPU")
    print(f"\n  ⚡ Device: {device_name} ({'cuda:' + device if use_gpu else 'cpu'})")

    # ── Load models ───────────────────────────────────────
    from ultralytics import YOLO

    print("Loading person detection model...")
    person_model = YOLO(person_model_path)
    person_model.to(f"cuda:{device}" if use_gpu else "cpu")
    print("Loading ROI classification model...")
    roi_cls_model = YOLO(roi_cls_model_path)
    roi_cls_model.to(f"cuda:{device}" if use_gpu else "cpu")

    # ── Open video ────────────────────────────────────────
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_name = Path(video_path).stem

    # Frame skip interval
    skip = max(1, int(video_fps / process_fps))

    print(f"\n{'='*60}")
    print(f"  AI Camera — Inference Pipeline")
    print(f"{'='*60}")
    print(f"  Video:     {video_path}")
    print(f"  Device:    {device_name} ({'cuda:' + device if use_gpu else 'cpu'})")
    print(f"  FPS:       {video_fps:.1f} (process every {skip} frames)")
    print(f"  Size:      {frame_w}x{frame_h}")
    print(f"  Frames:    {total_frames}")
    print(f"  Workers:   {len(worker_rois)} ROIs")
    print(f"  Buffers:   {len(buffer_rois)} ROIs")
    print(f"  T_absent:  {t_absent}s")
    print(f"  T_backlog: {t_backlog}s")
    print(f"{'='*60}\n")

    # ── Setup output ──────────────────────────────────────
    ensure_dir(os.path.dirname(output_path) or "outputs/videos")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_writer = cv2.VideoWriter(output_path, fourcc,
                                 min(process_fps, video_fps),
                                 (frame_w, frame_h))

    # Snapshot dir
    snap_dir = os.path.join("outputs", "snapshots", video_name)
    ensure_dir(snap_dir)

    # Event logger
    log_path = os.path.join("outputs", "logs", f"{video_name}_events.csv")
    logger = EventLogger(log_path, video_name=video_name,
                         camera_id=camera_id)

    # ── Initialize trackers / rules ───────────────────────
    # Per-worker-ROI: presence tracker + absence rule
    worker_trackers = {}
    worker_rules = {}
    for wroi in worker_rois:
        wid = wroi["id"]
        worker_trackers[wid] = PresenceTracker(grace_frames=grace)
        worker_rules[wid] = WorkerAbsenceRule(wid, threshold_sec=t_absent)

    # Per-buffer-ROI: state smoother + backlog rule
    buffer_smoothers = {}
    buffer_rules = {}
    for broi in buffer_rois:
        bid = broi["id"]
        buffer_smoothers[bid] = StateSmoother(window_size=smooth_window)
        buffer_rules[bid] = BacklogRule(
            bid, threshold_sec=t_backlog,
            trigger_states=trigger_states)

    # ── Main loop ─────────────────────────────────────────
    frame_idx = 0
    processed = 0
    t_start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % skip != 0:
            frame_idx += 1
            continue

        current_sec = frame_to_sec(frame_idx, video_fps)
        display = frame.copy()

        # ─── Step 1: Person detection + tracking ──────────
        results = person_model.track(
            source=frame,
            imgsz=imgsz_detect,
            conf=conf_detect,
            tracker=tracker_cfg,
            persist=True,
            verbose=False,
            device=f"cuda:{device}" if use_gpu else "cpu",
        )

        person_bboxes = []
        track_ids = []

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i])
                if cls_id == 0:  # person class
                    x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)
                    tid = int(boxes.id[i]) if boxes.id is not None else -1
                    person_bboxes.append((x1, y1, x2, y2))
                    track_ids.append(tid)

                    # Draw person bbox
                    draw_person_bbox(display, x1, y1, x2, y2,
                                     track_id=tid)

        # ─── Step 2: Worker ROI analysis ──────────────────
        alert_banners = []

        for wroi in worker_rois:
            wid = wroi["id"]
            pts = wroi["points"]

            # Find persons in this worker ROI
            ids_in_roi = filter_persons_in_roi(
                person_bboxes, track_ids, pts)
            person_present = len(ids_in_roi) > 0

            # Update presence tracker (with grace period)
            stable_present = worker_trackers[wid].update(person_present)

            # Update rule engine
            event = worker_rules[wid].update(stable_present, current_sec)

            # Draw worker ROI
            roi_color = COLOR_GREEN if stable_present else COLOR_YELLOW
            draw_polygon(display, pts, color=roi_color,
                         label=f"{wid} ({'OK' if stable_present else 'ABSENT'})")

            # Handle events
            if event:
                if event["action"] == "start":
                    snap_path = ""
                    if snapshot_on_alert:
                        snap_name = (f"{video_name}_{wid}_absence_"
                                     f"{current_sec:.0f}s.jpg")
                        snap_path = os.path.join(snap_dir, snap_name)
                        cv2.imwrite(snap_path, frame)

                    logger.log_event(
                        roi_id=wid,
                        event_type="worker_absence_start",
                        start_sec=event["start_sec"],
                        end_sec=current_sec,
                        trigger_state="absent",
                        snapshot_path=snap_path,
                    )
                    print(f"[{sec_to_mmss(current_sec)}] "
                          f"⚠ ALERT: {wid} absent > {t_absent}s")

                elif event["action"] == "end":
                    logger.log_event(
                        roi_id=wid,
                        event_type="worker_absence_end",
                        start_sec=event["start_sec"],
                        end_sec=current_sec,
                        trigger_state="returned",
                    )
                    print(f"[{sec_to_mmss(current_sec)}] "
                          f"✓ CLEARED: {wid} returned")

            # Alert banner
            if worker_rules[wid].is_alert:
                elapsed = worker_rules[wid].get_elapsed(current_sec)
                alert_banners.append(
                    f"⚠ {wid}: ABSENT {sec_to_mmss(elapsed)}")
                draw_timer(display, pts[0][0], pts[0][1] - 25,
                           elapsed, "Absent", COLOR_RED)

        # ─── Step 3: Buffer ROI analysis ──────────────────
        for broi in buffer_rois:
            bid = broi["id"]
            pts = broi["points"]

            # Crop ROI region
            crop = crop_polygon_region_for_cls(frame, pts)

            raw_state = "unknown"
            if crop is not None and crop.size > 0:
                # Classify
                cls_results = roi_cls_model.predict(
                    source=crop,
                    imgsz=imgsz_cls,
                    conf=conf_cls,
                    verbose=False,
                    device=f"cuda:{device}" if use_gpu else "cpu",
                )
                if cls_results and cls_results[0].probs is not None:
                    probs = cls_results[0].probs
                    top_idx = int(probs.top1)
                    class_names = cls_results[0].names
                    raw_state = class_names.get(top_idx, "unknown")

            # Smooth
            stable_state = buffer_smoothers[bid].update(raw_state)

            # Draw ROI with state
            draw_roi_state(display, pts, stable_state, roi_id=bid)

            # Update rule engine
            event = buffer_rules[bid].update(stable_state, current_sec)

            if event:
                if event["action"] == "start":
                    snap_path = ""
                    if snapshot_on_alert:
                        snap_name = (f"{video_name}_{bid}_backlog_"
                                     f"{current_sec:.0f}s.jpg")
                        snap_path = os.path.join(snap_dir, snap_name)
                        cv2.imwrite(snap_path, frame)

                    logger.log_event(
                        roi_id=bid,
                        event_type="backlog_alert_start",
                        start_sec=event["start_sec"],
                        end_sec=current_sec,
                        trigger_state=event.get("trigger_state", ""),
                        snapshot_path=snap_path,
                    )
                    print(f"[{sec_to_mmss(current_sec)}] "
                          f"⚠ ALERT: {bid} backlog ({stable_state}) "
                          f"> {t_backlog}s")

                elif event["action"] == "end":
                    logger.log_event(
                        roi_id=bid,
                        event_type="backlog_alert_end",
                        start_sec=event["start_sec"],
                        end_sec=current_sec,
                        trigger_state="cleared",
                    )
                    print(f"[{sec_to_mmss(current_sec)}] "
                          f"✓ CLEARED: {bid} back to normal")

            if buffer_rules[bid].is_alert:
                elapsed = buffer_rules[bid].get_elapsed(current_sec)
                alert_banners.append(
                    f"⚠ {bid}: {stable_state.upper()} "
                    f"{sec_to_mmss(elapsed)}")

        # ─── Step 4: Draw alerts and info ─────────────────
        for i, banner_text in enumerate(alert_banners):
            draw_alert_banner(display, banner_text,
                              y_offset=i * 42)

        # Info panel
        info_lines = [
            f"Frame: {frame_idx}/{total_frames}",
            f"Time:  {sec_to_mmss(current_sec)}",
            f"Persons: {len(person_bboxes)}",
        ]
        draw_info_panel(display, info_lines)

        # ─── Step 5: Write output ─────────────────────────
        out_writer.write(display)

        if show_preview:
            cv2.imshow("AI Camera Preview", display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Preview stopped by user.")
                break

        processed += 1
        frame_idx += 1

        # Progress
        if processed % 100 == 0:
            elapsed_real = time.time() - t_start
            speed = processed / elapsed_real if elapsed_real > 0 else 0
            print(f"  Processed {processed} frames "
                  f"({speed:.1f} fps) "
                  f"@ {sec_to_mmss(current_sec)}")

    # ── Cleanup ───────────────────────────────────────────
    cap.release()
    out_writer.release()
    if show_preview:
        cv2.destroyAllWindows()

    elapsed_total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  Pipeline complete!")
    print(f"  Frames processed: {processed}")
    print(f"  Time:  {elapsed_total:.1f}s")
    print(f"  Speed: {processed/elapsed_total:.1f} fps")
    print(f"  Output video: {output_path}")
    print(f"  Event log:    {log_path}")
    print(f"  Snapshots:    {snap_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Camera — Full Inference Pipeline"
    )
    parser.add_argument("--video", required=True,
                        help="Input video path")
    parser.add_argument("--roi", required=True,
                        help="ROI config JSON path")
    parser.add_argument("--rules", required=True,
                        help="Rules YAML path")
    parser.add_argument("--person_model", required=True,
                        help="Person detection model weights")
    parser.add_argument("--roi_cls_model", required=True,
                        help="ROI state classification model weights")
    parser.add_argument("--output", default="outputs/videos/demo_output.mp4",
                        help="Output video path")
    parser.add_argument("--runtime", default=None,
                        help="Runtime YAML config (optional)")
    parser.add_argument("--tracker", default="bytetrack.yaml",
                        help="Tracker config (default: bytetrack.yaml)")
    parser.add_argument("--device", default="auto",
                        help="Device: auto, 0, 1, cpu (default: auto → GPU if available)")
    parser.add_argument("--preview", action="store_true",
                        help="Show live preview window")
    args = parser.parse_args()

    run_pipeline(
        video_path=args.video,
        roi_path=args.roi,
        rules_path=args.rules,
        person_model_path=args.person_model,
        roi_cls_model_path=args.roi_cls_model,
        output_path=args.output,
        runtime_path=args.runtime,
        tracker_cfg=args.tracker,
        show_preview=args.preview,
        device=args.device,
    )


if __name__ == "__main__":
    main()
