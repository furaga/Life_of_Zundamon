import cv2
from rembg import remove
from pathlib import Path
import numpy as np
import os


def imread_safe(filename, flags=cv2.IMREAD_COLOR, dtype=np.uint8):
    try:
        n = np.fromfile(filename, dtype)
        img = cv2.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None


def imwrite_safe(filename, img, params=None):
    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img, params)

        if result:
            with open(filename, mode="w+b") as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


# for img_path in list(Path("data/mk8dx_images/items").glob("*.png")):
#     input = imread_safe(str(img_path))
#     print(img_path)
#     print(input.shape)
#     output = remove(input)
#     out_path = "data/mk8dx_images/items_rembg/" + img_path.name
#     print("Output:", out_path)
#     imwrite_safe(str(out_path), output)


for img_path in list(Path("data/mk8dx_images/place").glob("*.png")):
    input = imread_safe(str(img_path))
    print(img_path)
    print(input.shape)
    output = remove(input)
    out_path = "data/mk8dx_images/place_rembg/" + img_path.name
    print("Output:", out_path)
    imwrite_safe(str(out_path), output)
#    cv2.imshow("img", output)
#    cv2.waitKey(0)
