from __future__ import annotations

import json
import os
import uuid
from typing import Dict, List, Optional


class CameraStore:
    def __init__(self, path: str = "storage/cameras.json") -> None:
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def ensure_seed_file(self) -> None:
        if os.path.exists(self.path):
            return
        self.save_all(self.default_cameras())

    def default_cameras(self) -> List[Dict]:
        return [
            {
                "camera_uid": "cam_001",
                "display_name": "Camera 1",
                "source_mode": "video",
                "source_value": "assets/videos/cam01_video1.mp4",
                "roi_path": "configs/roi_cam01.json",
                "enabled": True,
            },
            {
                "camera_uid": "cam_002",
                "display_name": "Camera 2",
                "source_mode": "video",
                "source_value": "assets/videos/cam02_video2.mp4",
                "roi_path": "configs/roi_cam02.json",
                "enabled": True,
            },
            {
                "camera_uid": "cam_003",
                "display_name": "Camera 3",
                "source_mode": "video",
                "source_value": "assets/videos/cam03_video3.mp4",
                "roi_path": "configs/roi_cam03.json",
                "enabled": True,
            },
            {
                "camera_uid": "cam_004",
                "display_name": "Camera 4",
                "source_mode": "none",
                "source_value": "",
                "roi_path": "configs/roi_cam04.json",
                "enabled": True,
            },
        ]

    def load_all(self) -> List[Dict]:
        self.ensure_seed_file()
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data

    def save_all(self, cameras: List[Dict]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(cameras, f, ensure_ascii=False, indent=2)

    def create_camera(
        self,
        display_name: str,
        source_mode: str = "none",
        source_value: str = "",
        roi_path: str = "configs/roi_cam01.json",
        enabled: bool = True,
    ) -> Dict:
        return {
            "camera_uid": "cam_{}".format(uuid.uuid4().hex[:8]),
            "display_name": display_name,
            "source_mode": source_mode,
            "source_value": source_value,
            "roi_path": roi_path,
            "enabled": enabled,
        }

    def get_by_uid(self, camera_uid: str) -> Optional[Dict]:
        for cam in self.load_all():
            if cam.get("camera_uid") == camera_uid:
                return cam
        return None

    def upsert(self, camera: Dict) -> None:
        cameras = self.load_all()
        uid = camera.get("camera_uid")
        replaced = False
        for idx, cam in enumerate(cameras):
            if cam.get("camera_uid") == uid:
                cameras[idx] = camera
                replaced = True
                break
        if not replaced:
            cameras.append(camera)
        self.save_all(cameras)

    def delete(self, camera_uid: str) -> None:
        cameras = [c for c in self.load_all() if c.get("camera_uid") != camera_uid]
        self.save_all(cameras)