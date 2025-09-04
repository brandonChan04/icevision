# predict.py
# Load your trained weights and run inference on:
#  1) the entire validation folder, and
#  2) a single sample image

from ultralytics import YOLO
from pathlib import Path

BEST_PT = r"C:\Users\brandon\html2\iceVision_model\runs\detect\train\weights\best.pt"
VAL_DIR = r"C:\Users\brandon\html2\iceVision_model\icevision\files\images\val"
VAL_SAMPLE = r"C:\Users\brandon\html2\iceVision_model\icevision\files\images\val\video4_frame25.png"

def main():
    model = YOLO(BEST_PT)

    # A) batch over the whole val folder; saves images with boxes to runs/detect/predict/
    model.predict(source=VAL_DIR, conf=0.25, save=True)

    # B) single image quick view (optional)
    if Path(VAL_SAMPLE).exists():
        r = model(VAL_SAMPLE)
        r[0].show()
    else:
        print(f"[WARN] VAL_SAMPLE not found: {VAL_SAMPLE}")

if __name__ == "__main__":
    main()
