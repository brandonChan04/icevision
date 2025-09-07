# app.py — FastAPI wrapper around best.onnx (image + video)
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np, cv2, onnxruntime as ort, os, traceback, tempfile
from pathlib import Path

# ---- settings ----
MODEL_PATH = os.getenv(
    "MODEL_PATH",
    r"C:\Users\brandon\html2\iceVision_model\runs\detect\train\weights\best.onnx"
)
IMG_SIZE = int(os.getenv("IMG_SIZE", "864"))  # export rounded to 864
CLASS_NAMES = ["player"]  # class 0 -> player

# ---- load model ----
sess = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])

app = FastAPI(title="IceVision API", version="1.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later: restrict to your Vercel domain(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- helpers ----
def preprocess_bgr(img_bgr: np.ndarray, size: int):
    """Letterbox to square (top-left), return blob [1,3,H,W] and scale to undo later."""
    h, w = img_bgr.shape[:2]
    scale = min(size / h, size / w)
    nh, nw = int(h * scale), int(w * scale)
    pad = np.full((size, size, 3), 114, dtype=np.uint8)
    rsz = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pad[:nh, :nw] = rsz
    blob = pad.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return blob, scale

def _xywh2xyxy(xywh):
    x, y, w, h = xywh
    return np.array([x - w / 2, y - h / 2, x + w / 2, y + h / 2], dtype=np.float32)

def postprocess(pred, scale, conf=0.25):
    """
    Accepts ONNX output in either:
      - [1, C, N]  (channels-first)
      - [1, N, C]
    Returns list of dicts with xyxy (pixel coords in original image), conf, cls, label.
    """
    p = pred
    if p.ndim != 3:
        raise ValueError(f"Unexpected prediction ndim: {p.ndim}, shape={p.shape}")

    # Make shape [1, N, C]
    if p.shape[1] in (5, 6, 7, 84):  # channels-first common widths
        p = np.transpose(p, (0, 2, 1))

    N, C = p.shape[1], p.shape[2]
    boxes = []
    for i in range(N):
        r = p[0, i]
        if C >= 6:
            xywh = r[:4]
            obj_conf = float(r[4])
            if C > 6:
                class_scores = r[5:]
                cls_id = int(np.argmax(class_scores))
                cls_conf = float(class_scores[cls_id])
                score = obj_conf * cls_conf
            else:
                cls_id = 0
                score = obj_conf
        elif C == 5:
            xywh = r[:4]
            score = float(r[4])
            cls_id = 0
        else:
            continue

        if score < conf:
            continue

        x1, y1, x2, y2 = _xywh2xyxy(xywh)
        x1, y1, x2, y2 = x1 / scale, y1 / scale, x2 / scale, y2 / scale

        boxes.append({
            "xyxy": [float(x1), float(y1), float(x2), float(y2)],
            "conf": float(score),
            "cls": int(cls_id),
            "label": CLASS_NAMES[int(cls_id)] if int(cls_id) < len(CLASS_NAMES) else str(int(cls_id))
        })
    return boxes

def infer_image_bgr(img_bgr: np.ndarray, conf: float):
    """Run full pipeline on a single BGR image and return (boxes, w, h)."""
    blob, scale = preprocess_bgr(img_bgr, IMG_SIZE)
    outputs = sess.run(None, {"images": blob})
    pred = outputs[0]
    boxes = postprocess(pred, scale, conf)
    h, w = img_bgr.shape[:2]
    return boxes, w, h

# ---- routes ----
@app.post("/predict")
async def predict(file: UploadFile = File(...), conf: float = 0.25):
    try:
        data = np.frombuffer(await file.read(), np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            return JSONResponse({"error": "Invalid image"}, status_code=400)

        boxes, w, h = infer_image_bgr(img, conf)
        return JSONResponse({
            "boxes": boxes,
            "img_w": w,
            "img_h": h,
            "model": "icevision-v1"
        })
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/predict_video")
async def predict_video(
    file: UploadFile = File(...),
    conf: float = 0.25,
    every_n: int = 5,         # sample every Nth frame
    max_frames: int = 300     # cap returned frames to keep JSON reasonable
):
    """
    Upload a video (e.g., .mp4). The API samples frames, runs detection,
    and returns per-frame boxes. Coordinates are in original frame pixels.
    """
    # Persist to a temp file so OpenCV can open it
    suffix = Path(file.filename or "").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            return JSONResponse({"error": "Unable to open video"}, status_code=400)

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        frames = []
        i = 0
        kept = 0
        while kept < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if i % max(1, every_n) == 0:
                boxes, w, h = infer_image_bgr(frame, conf)
                frames.append({
                    "i": i,
                    "boxes": boxes,
                    "img_w": int(w),
                    "img_h": int(h),
                })
                kept += 1
            i += 1

        cap.release()
        return JSONResponse({
            "fps": fps,
            "total_frames": total,
            "sampled_every_n": every_n,
            "returned_frames": len(frames),
            "frames": frames,
            "model": "icevision-v1"
        })
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass

@app.get("/")
def health():
    return {"ok": True, "model": "icevision-v1"}
