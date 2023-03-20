from obswebsocket import obsws, requests


# テキスト変更関数
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

#print(ws.call(requests.GetSourceSettings()))  # "from-python", "text"))
import time

obsTextChange("from-python", "HELLO OBS WEBSOCKET")
time.sleep(1.0)
obsTextChange("from-python", "HELLO")
time.sleep(1.0)
obsTextChange("from-python", "OBS")
time.sleep(1.0)
obsTextChange("from-python", "WORLD!!!!!")
time.sleep(1.0)
# print(ws.call(requests.GetVersion()).getVersion())

ws.disconnect()
