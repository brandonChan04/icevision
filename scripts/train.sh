yolo train \
model=yolo12m.pt \
data=/home/kerdizheng/Desktop/icevision/data/data.yaml \
epochs=250 \
imgsz=854 \
batch=4 \
cache=True \
device=0 \
project=icevision_v1 \
rect=True \
plots=True \
fliplr=0.6


yolo export \
model=/home/kerdizheng/Desktop/icevision/icevision_v1/train3/weights/best.pt \
format=onnx \
imgsz=854 


# w 854
# h 480