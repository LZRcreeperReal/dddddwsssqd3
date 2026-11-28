#!/usr/bin/env python3
"""Cut out the main car in every frame -> RGBA pngs. Keeps only the biggest blob (drops background people/cars).
usage: python3 cutout_seq.py in_dir out_dir [model]"""
import glob, os, sys
import numpy as np, cv2
from rembg import new_session, remove
from PIL import Image


def biggest(alpha):
    m = (alpha > 127).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return alpha
    k = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    keep = cv2.dilate((lab == k).astype(np.uint8), np.ones((9, 9), np.uint8))
    return (alpha * keep).astype(np.uint8)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    s = new_session(sys.argv[3] if len(sys.argv) > 3 else "isnet-general-use")
    for f in sorted(glob.glob(src + "/*.png")):
        im = np.array(remove(Image.open(f), session=s))
        im[..., 3] = biggest(im[..., 3])
        Image.fromarray(im).save(os.path.join(dst, os.path.basename(f)))
