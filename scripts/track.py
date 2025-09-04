from ultralytics import YOLO
from pathlib import Path

BEST_PT   = r"C:\Users\brandon\html2\iceVision_model\runs\detect\train\weights\best.pt"
VIDEO_SRC = r"C:\Users\brandon\html2\iceVision_model\icevision\trials\vid.mp4"   # or "0" for webcam

def main():
    model = YOLO(BEST_PT)

    # BYTETrack is bundled with Ultralytics; this runs detection + tracking and writes an output video.
    model.track(
        source=VIDEO_SRC,          # file path or 0 for webcam
        tracker="bytetrack.yaml",  # built-in tracker config
        imgsz=854,                 # try 640 for more speed on CPU
        conf=0.25,
        vid_stride=1,              # increase to 2-3 to skip frames for speed
        persist=True,              # keep track IDs consistent
        show=True,                 # display a live window
        save=True,                 # write output to runs/track/predict/
        device="cpu"               # use "0" if you have an NVIDIA GPU
    )

if __name__ == "__main__":
    main()
