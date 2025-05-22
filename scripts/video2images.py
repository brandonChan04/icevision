# given an mp4 file, randomly select N frames
# save these frames to a pre-defined target

import random
import av
import cv2 as cv
import sys
import os
import numpy as np

def sample_random_frames(path: str, num_frames: int) -> np.ndarray:
    """
    Open the video at `path`, pick `num_frames` distinct random
    frame‐indices, seek to each one and decode exactly that frame.
    Returns a NumPy array of shape (num_frames, H, W, 3) in RGB uint8.
    """
    container = av.open(path)
    vs = container.streams.video[0]

    # 1) figure out fps
    fps = float(vs.average_rate)
    if fps <= 0:
        raise RuntimeError("Can't determine frame rate")

    # 2) figure out total frames
    if vs.frames:
        total = vs.frames
    else:
        # fallback: use container.duration (microseconds)  
        # divided by 1e6 to get seconds
        if container.duration is None:
            raise RuntimeError("Can't determine video duration")
        total = int((container.duration / 1_000_000) * fps)

    if num_frames > total:
        raise ValueError(f"num_frames ({num_frames}) > total frames ({total})")

    # 3) pick distinct random indices
    picks = sorted(random.sample(range(total), num_frames))

    out = []
    for idx in picks:
        # desired timestamp in seconds
        t_seconds = idx / fps

        # convert to stream‐time_base units (ticks)
        # stream.time_base is a Fraction seconds per tick
        ticks = int(t_seconds / float(vs.time_base))

        # seek to nearest keyframe before ticks
        container.seek(ticks, any_frame=False, backward=True, stream=vs)

        # now decode until we hit pts >= ticks
        for frame in container.decode(vs):
            if frame.pts is None:
                continue
            if frame.pts >= ticks:
                img = frame.to_ndarray(format="rgb24")
                out.append(img)
                break

    container.close()
    # stack into a single array
    return np.stack(out, axis=0)

    

if __name__ == "__main__":
    target = "/home/kerdizheng/Desktop/ice_vision/images"
    videos_path = "/home/kerdizheng/Desktop/ice_vision/videos"
    
    for video_num, video in enumerate(os.listdir(videos_path)):
        print(f"Processing video {video_num}")
        video_path = os.path.join(videos_path, video)
        frames = sample_random_frames(video_path, 45)
        
        for frame_num, f in enumerate(frames):
            img_path = os.path.join(target, f"video{video_num}_frame{frame_num}.png")
            bgr = f[..., ::-1]
            cv.imwrite(img_path, bgr)
            