from obswebsocket import obsws, requests
import time
from datetime import datetime
from pathlib import Path

host = "localhost"
port = 4444
password = "GKzsYMK574JexVLr"

ws = obsws(host, port, password)
ws.connect()


prev_time = time.time()
while True:
    now = datetime.now()
    out_path = Path(
        f"C:/Users/furag/Documents/prog/python/Life_of_Zundamon/record_items/{now.strftime('%Y-%m-%dT%H-%M-%S.png')}"
    )
    print(out_path)
    since = time.time()
    ws.call(
        requests.TakeSourceScreenshot(
            # sourceName="映像キャプチャデバイス",
            sourceName="映像キャプチャデバイス",
            embedPictureFormat="jpg",
            saveToFilePath=str(out_path),
            #            width = 1920,
            #           height = 1080,
            #          compressionQuality = 100,
        )
    )
    print(f"[A] Elapsed {time.time() - since:.2f} sec")

    while time.time() - prev_time < 1:
        time.sleep(0.1)
    prev_time = time.time()
