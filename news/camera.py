import asyncio
import datetime
import os
import pathlib
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple, List

import cv2
import numpy as np

time_since_last_motion = 0
time_since_motion_begin = 0

class Camera:
    def __init__(self, url):
        self.url = url
        self.cap: Optional[cv2.VideoCapture] = None
        self.open_capture()

    def open_capture(self):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        time.sleep(0.25)
        start = time.time()
        ok, _ = self.cap.read()
        while not ok and (time.time() - start) < 30:
            time.sleep(0.25)
            ok, _ = self.cap.read()

    def open_if_none(self):
        if self.cap is None:
            self.open_capture()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def read(self):
        self.open_if_none()
        if self.cap is None:
            return None
        return self.cap.read()

class Process:
    def __init__(self, camera: Camera, history=500):
        self.camera = camera
        self.frame = None
        self.motion_subtractor = cv2.createBackgroundSubtractorMOG2(history=history, varThreshold=16, detectShadows=True)
        self.motion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


    def fetch_frame(self) -> bool:
        ok, self.frame = self.camera.read()
        return ok and self.frame is not None

    def get_motion(self, min_area = 1500):
        frame = self.frame.copy()

        fgmask = self.motion_subtractor.apply(frame)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, self.motion_kernel, iterations=2)
        fgmask = cv2.dilate(fgmask, self.motion_kernel, iterations=2)

        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_count = 0
        relevant_contours = []
        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue
            relevant_contours.append(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            motion_count += 1

        cv2.putText(frame, f"Motion regions: {motion_count}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if motion_count else (0, 0, 255), 2)

        return motion_count, relevant_contours, frame


def run(url = "rtsp://192.168.69.3:8554/room", output_dir = "movement"):
    camera = Camera(url)

    subtractor = cv2.createBackgroundSubtractorMOG2(history=100, varThreshold=32, detectShadows=True)
    # subtractor = cv2.createBackgroundSubtractorKNN(history=100, detectShadows=True)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    min_area = 1500

    frames = 0
    last_time = time.time()

    while True:
        ok, frame = camera.read()
        if not ok:
            continue
        frames += 1

        if last_time + 1 < time.time():
            last_time = time.time()
            print(f"FPS: {frames}")
            frames = 0

        if frames % 5 != 0:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.equalizeHist(gray, gray)

        fgmask = subtractor.apply(frame)
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=2)
        fgmask = cv2.dilate(fgmask, kernel, iterations=2)

        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        render_frame = frame.copy()

        motion_count = 0
        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            cv2.rectangle(render_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            motion_count += 1


        cv2.putText(render_frame, f"Motion regions: {motion_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if motion_count else (0, 0, 255), 2)

        if motion_count > 0:
            output = pathlib.Path(output_dir + "/" + time.strftime("%Y-%m/%d/"))
            output.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output / (time.strftime("%H_%M_%S_") + str(datetime.datetime.now().microsecond)
                                      + ".MC_" + str(motion_count) + ".jpg")), render_frame)

        # cv2.imshow('VIDEO', render_frame)
        # cv2.imshow('MOTION', fgmask)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run()

# Example usage (manual testing):
# if __name__ == "__main__":
#     url = "rtsp://user:pass@ip-address:554/stream"
#     proc = build_camera_pipeline(url, source_name="FrontDoor", target_width=960, target_height=540)
#     async def run():
#         await proc.start_async()
#         try:
#             while True:
#                 det = await proc.events.get()
#                 print(f"[{time.strftime('%X', time.localtime(det.ts))}] {det.source} detected {det.count} person(s)")
#                 with open(f"detection_{int(det.ts)}.jpg", "wb") as f:
#                     f.write(det.jpg_bytes)
#         finally:
#             await proc.stop_async()
#     asyncio.run(run())