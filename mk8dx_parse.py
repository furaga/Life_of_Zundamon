import requests
import pytchat
import time
import argparse
import cv2
from pathlib import Path
from utils import MK8DX


# コマンド引数
parser = argparse.ArgumentParser(description="TALK")
args = parser.parse_args()


def init():
    MK8DX.init(Path("data/mk8dx_images"))


def main():
    init()

    all_img_paths = list(Path("record").glob("*.png"))

    for img_path in all_img_paths[300:]:
        img = cv2.imread(str(img_path))

        since = time.time()

        ret, n_coin = MK8DX.detect_coin(img)
        if not ret or not (0 <= n_coin <= 10):
            continue

        ret, n_lap = MK8DX.detect_lap(img)
        if not ret or not (0 <= n_lap <= 7):
            continue

        omote, ura = MK8DX.detect_items(img)
        if omote[0] < 0.81:
            omote = [0, "none"]
        if omote[1] == "none" or ura[0] < 0.7:
            ura = [0, "none"]

        place = MK8DX.detect_place(img)
        if place[0] < 0.7:
            place = [0, "-1"]

        print(f"Coin  : {n_coin}")
        print(f"Lap   : {n_lap}")
        print(f"Items : {omote}, {ura}")
        print(f"Place : {place}")
        print(f"[parse] Elapsed {time.time() - since:.2f} sec")

        # 大きくて画面に入らないので小さく
        img_resize = cv2.resize(img, None, fx=0.5, fy=0.5)
        cv2.imshow("screenshot", img_resize)
        if ord('q') == cv2.waitKey(0):
            break


if __name__ == "__main__":
    main()
