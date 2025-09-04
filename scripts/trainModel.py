# trainModel.py
# Train (or resume) YOLO on your hockey dataset, then validate and smoke-test.

from ultralytics import YOLO
from pathlib import Path

# --- Paths (edit if you move things) ---
DATA_YAML = r"C:\Users\brandon\html2\iceVision_model\icevision\files\data.yaml"
VAL_SAMPLE = r"C:\Users\brandon\html2\iceVision_model\icevision\files\images\val\video4_frame25.png"

# If you want to RESUME later from an existing run, set this to your previous best.pt.
RESUME_FROM = None  # e.g., r"C:\Users\brandon\html2\iceVision_model\runs\detect\train\weights\best.pt"

# Otherwise start from a pretrained checkpoint (recommended for a new run)
PRETRAINED = "yolo11n.pt"

# Training knobs you’ll likely tweak later
EPOCHS = 100
IMGSZ = 854
BATCH = 4
DEVICE = "cpu"    # "0" for GPU, "cpu" otherwise

def main():
    # 1) Load model (resume or start from pretrained)
    model = YOLO(RESUME_FROM if RESUME_FROM else PRETRAINED)

    # 2) Train
    train_results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        device=DEVICE,
        rect=True,          # better for 16:9 rink frames
        plots=True,         # saves learning curves
        project=r"C:\Users\brandon\html2\iceVision_model\runs\detect",
        name="train",       # run folder name (will auto-increment if exists)
    )

    # 3) Validate (mAP/precision/recall on val split)
    metrics = model.val()

    # 4) Quick predict on a known val image (smoke test)
    if Path(VAL_SAMPLE).exists():
        r = model(VAL_SAMPLE)
        r[0].show()
    else:
        print(f"[WARN] VAL_SAMPLE not found: {VAL_SAMPLE}")

    # 5) Optional: export for portable inference (ONNX)
    export_path = model.export(format="onnx")
    print(f"[INFO] Exported ONNX: {export_path}")

if __name__ == "__main__":
    main()
