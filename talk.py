from argparse import ArgumentParser
import pytchat
from obswebsocket import obsws, requests
import time

# obswebsocket
host = "localhost"
port = 4444
password = "GKzsYMK574JexVLr"
ws = obsws(host, port, password)
ws.connect()

# pytchat
chat = pytchat.create(video_id="U5uMBS4kBuY")


def obsTextChange(source_name: str, strtext: str):
    ws.call(
        requests.SetSourceSettings(
            sourceName=source_name, sourceSettings={"text": strtext}
        )
    )


def init():
    ws.connect()


def listen():
    if not chat.is_alive():
        print("ERROR: chat is dead.")
        time.sleep(0.1)
        exit()
    chats = [c for c in chat.get().sync_items()]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


def think(author, prompt):
    # TODO: OpenAI APIで回答生成
    if prompt == "初見です":
        return "初見は帰るのだ"
    answer = prompt
    return answer


def speak(text):
    # TODO: OBSの字幕変更
    # TODO: VOICEVOXで回答を喋らせる
    obsTextChange("zundamon_zimaku", text)
    print(text)
    time.sleep(3.0)


def main(args) -> None:
    init()
    while True:
        ret, author, prompt = listen()
        if not ret:
            continue
        speak("「" + prompt + "」")
        answer = think(author, prompt)
        speak(answer)


def parse_args():
    argparser = ArgumentParser()
    args = argparser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())
