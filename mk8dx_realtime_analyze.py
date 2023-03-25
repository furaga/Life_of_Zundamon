from obswebsocket import obsws, requests
import time
from datetime import datetime
from pathlib import Path
from utils import MK8DX
import cv2


def obsTextChange(source_name: str, strtext: str):
    ws.call(
        requests.SetSourceSettings(
            sourceName=source_name, sourceSettings={"text": strtext}
        )
    )


host = "localhost"
port = 4444
password = "GKzsYMK574JexVLr"

ws = obsws(host, port, password)
ws.connect()

MK8DX.init(Path("data/mk8dx_images"))

prev_time = time.time()
while True:
    time.sleep(0.01)

    since = time.time()
    out_path = Path("C:/Users/furag/Documents/prog/python/Life_of_Zundamon/__tmp__.jpg")
    ws.call(
        requests.TakeSourceScreenshot(
            sourceName="映像キャプチャデバイス",
            embedPictureFormat="jpg",
            saveToFilePath=str(out_path),
        )
    )

    print(f"[A] Elapsed {time.time() - since:.2f} sec")
    since = time.time()

    img = cv2.imread(str(out_path))

    print(f"[B] Elapsed {time.time() - since:.2f} sec")
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

    print(f"[C] Elapsed {time.time() - since:.2f} sec")
    since = time.time()

    text = f"Coin  : {n_coin}\n"
    text += f"Lap   : {n_lap}\n"
    text += f"Items : {omote}, {ura}\n"
    text += f"Place : {place}\n"
    obsTextChange("current_mk8dx_info", text)


    print(f"[D] Elapsed {time.time() - since:.2f} sec")
    since = time.time()
