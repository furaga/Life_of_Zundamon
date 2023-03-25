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

history = []


def is_same_history_item(a, b):
    for i in range(2):
        if a[i] != b[i]:
            return False

    for i in range(2, 5):
        if a[i][1] != b[i][1]:
            return False

    return True


while True:
    since = time.time()
    out_path = Path("C:/Users/furag/Documents/prog/python/Life_of_Zundamon/__tmp__.jpg")
    ws.call(
        requests.TakeSourceScreenshot(
            sourceName="映像キャプチャデバイス",
            embedPictureFormat="jpg",
            saveToFilePath=str(out_path),
        )
    )

    # print(f"[A] Elapsed {time.time() - since:.2f} sec")
    # since = time.time()

    img = cv2.imread(str(out_path))

    # print(f"[B] Elapsed {time.time() - since:.2f} sec")
    # since = time.time()

    ret_coin, n_coin = MK8DX.detect_coin(img)
    ret_lap, n_lap = MK8DX.detect_lap(img)
    omote, ura = MK8DX.detect_items(img)
    if omote[0] < 0.81:
        omote = [0, "none"]
    if omote[1] == "none" or ura[0] < 0.7:
        ura = [0, "none"]

    place = MK8DX.detect_place(img)
    if place[0] < 0.7:
        place = [0, "-1"]

    history.append([n_coin, n_lap, omote, ura, place])

    if not ret_coin or not (0 <= n_coin <= 10):
        continue
    if not ret_lap or not (0 <= n_lap <= 3):
        continue
    if place[1] == "-1":
        continue

    # print(f"[C] Elapsed {time.time() - since:.2f} sec")
    # since = time.time()

    if len(history) >= 3:
        history = history[-3:]

    if len(history) < 3:
        continue

    # 3フレーム同じ結果だったら採用してOBS側を更新
    if not is_same_history_item(history[-1], history[-2]):
        continue
    if not is_same_history_item(history[-2], history[-3]):
        continue

    text = f"Coin  : {n_coin}\n"
    text += f"Lap   : {n_lap}\n"
    text += f"Items : {omote}, {ura}\n"
    text += f"Place : {place}\n"
    obsTextChange("current_mk8dx_info", text)

    print(f"[D] Elapsed {time.time() - since:.2f} sec")
    since = time.time()
