from argparse import ArgumentParser
import requests
import pytchat
import obswebsocket
import time
import json
import simpleaudio

# obswebsocket
host = "localhost"
port = 4444
password = "GKzsYMK574JexVLr"
ws = obswebsocket.obsws(host, port, password)
ws.connect()

# pytchat
chat = pytchat.create(video_id="U5uMBS4kBuY")

# voicevox
speaker = 1  # ずんだもん


def obsTextChange(source_name: str, strtext: str):
    ws.call(
        obswebsocket.requests.SetSourceSettings(
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


def tts(text):
    # 音声合成
    res1 = requests.post(
        "http://localhost:50021/audio_query",
        params={"text": text, "speaker": speaker},
    )
    res2 = requests.post(
        "http://localhost:50021/synthesis",
        params={"speaker": speaker},
        data=json.dumps(res1.json()),
    )
    return res2.content


def speak(text, wav):
    print(text)

    # OBSの字幕変更
    obsTextChange("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


def main(args) -> None:
    init()
    while True:
        ret, author, prompt = listen()
        if not ret:
            continue
        print("prompt:", prompt)

        answer = think(author, prompt)
        print("answer:", answer)

        prompt_wav = tts(prompt)
        answer_wav = tts(answer)
        print("tts done")

        speak("「" + prompt + "」", prompt_wav)
        time.sleep(0.5)
        speak(answer, answer_wav)
        print("spoken")


def parse_args():
    argparser = ArgumentParser()
    args = argparser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())
