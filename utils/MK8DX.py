import time
import openai
import os
import re
from pathlib import Path
from glob import glob
import cv2
import numpy as np
import clip
import torch

from . import digit_ocr


item_dict_ = {}
place_dict_ = {}


def cv2pil(image):
    from PIL import Image

    """OpenCV型 -> PIL型"""
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def imread_safe(filename, flags=cv2.IMREAD_COLOR, dtype=np.uint8):
    try:
        n = np.fromfile(filename, dtype)
        img = cv2.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None


ITEM_IMAGE_SIZE = 153


def get_clip_features(img):
    with torch.no_grad():
        p = cv2pil(img)
        image = clip_preprocess(p).unsqueeze(0).to(device)
        features = model.encode_image(image)
        return features.cpu().numpy()


def load_item_images(item_dir: Path):
    all_img_paths = list(item_dir.glob("*.webp"))
    all_img_paths += list(item_dir.glob("*.png"))
    for img_path in all_img_paths:
        img = imread_safe(str(img_path), cv2.IMREAD_UNCHANGED)
        img = cv2.resize(img, (ITEM_IMAGE_SIZE, ITEM_IMAGE_SIZE))
        mask = img[:, :, 3]
        rgb = img[:, :, :3]  # cv2.bitwise_and(img[:, :, :3], img[:, :, :3], mask=mask)
        feat = get_clip_features(rgb)
        feat /= np.linalg.norm(feat)
        item_dict_[img_path.stem] = mask, feat

    print("Loaded", len(item_dict_), "item images.")


def load_place_images(place_dir: Path):
    all_img_paths = list(place_dir.glob("*.png"))
    for img_path in all_img_paths:
        img = imread_safe(str(img_path))
        feat = get_clip_features(img)
        feat /= np.linalg.norm(feat)
        place_dict_[img_path.stem] = None, feat

    print("Loaded", len(place_dict_), "place images.")


device, model, clip_preprocess = None, None, None


def init(root_dir: Path):
    global device, model, clip_preprocess
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, clip_preprocess = clip.load("ViT-B/32", device)
    load_item_images(root_dir / "items")
    load_place_images(root_dir / "place")


def match(img_feat, ref_feat):
    similarity = img_feat @ ref_feat.T
    return similarity[0][0]


def detect_items(img):
    h, w = img.shape[:2]
    x1 = int(113 / 1280 * w)
    x2 = int(215 / 1280 * w)
    y1 = int(65 / 720 * h)
    y2 = int(167 / 720 * h)
    omote = img[y1:y2, x1:x2]
    omote_feat = get_clip_features(omote)
    omote_feat /= np.linalg.norm(omote_feat)

    x1 = int(48 / 1280 * w)
    x2 = int(112 / 1280 * w)
    y1 = int(38 / 720 * h)
    y2 = int(102 / 720 * h)
    ura = img[y1:y2, x1:x2]
    ura_feat = get_clip_features(ura)
    ura_feat /= np.linalg.norm(ura_feat)

    omote_ls = []
    ura_ls = []
    for item_name, (ref_mask, ref_feat) in item_dict_.items():
        omote_ls.append([match(omote_feat, ref_feat), item_name])
        ura_ls.append([match(ura_feat, ref_feat), item_name])

    omote_ls = sorted(omote_ls)
    ura_ls = sorted(ura_ls)
    # print("[omote]", omote_ls[-2:])
    # print("[ura  ]",ura_ls[-2:])

    return omote_ls[-1], ura_ls[-1]


# 現在の順位
def detect_place(img):
    h, w = img.shape[:2]
    x1 = int(1600 / 1920 * w)
    x2 = int(1820 / 1920 * w)
    y1 = int(840 / 1080 * h)
    y2 = int(1030 / 1080 * h)
    place_img = img[y1:y2, x1:x2]
    place_img_feat = get_clip_features(place_img)
    place_img_feat /= np.linalg.norm(place_img_feat)

    ls = []
    for item_name, (ref_mask, ref_feat) in place_dict_.items():
        ls.append([match(place_img_feat, ref_feat), item_name])

    ls = sorted(ls)
    # print(ls[-2:])

    return ls[-1]


def detect_number(img, verbose):
    coin_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, value = digit_ocr.detect_digit(coin_img, verbose)
    # print(ret, value)
    return ret, value


# コイン枚数
def detect_coin(img):
    h, w = img.shape[:2]
    x1 = int(133 / 1920 * w)
    x2 = int(214 / 1920 * w)
    y1 = int(972 / 1080 * h)
    y2 = int(1032 / 1080 * h)
    return detect_number(img[y1:y2, x1:x2], False)


# 何周目か
def detect_lap(img):
    h, w = img.shape[:2]
    x1 = int(300 / 1920 * w)
    x2 = int(345 / 1920 * w)
    y1 = int(972 / 1080 * h)
    y2 = int(1032 / 1080 * h)
    return detect_number(img[y1:y2, x1:x2], False)


if __name__ == "__main__":

    def main() -> None:
        init(Path("../data/mk8dx_images"))

        for img_path in Path("../record").glob("*.png"):
            img = cv2.imread(str(img_path))

            # since = time.time()
            # ret = detect_items(img)
            # print(f"[detect_items] Elapsed {time.time() - since:.2f} sec")

            # since = time.time()
            # ret = detect_place(img)
            # print(f"[detect_place] Elapsed {time.time() - since:.2f} sec")

            since = time.time()
            ret = detect_coin(img)
            since = time.time()
            ret = detect_lap(img)
            print(f"[detect coin/lap] Elapsed {time.time() - since:.2f} sec")

            # 大きくて画面に入らないので小さく
            img_resize = cv2.resize(img, None, fx=0.7, fy=0.7)
            cv2.imshow("screenshot", img_resize)
            cv2.waitKey(0)

    main()
