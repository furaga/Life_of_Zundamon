import requests
import pytchat
import obswebsocket
import time
import json
import simpleaudio
import random
import argparse

from utils import OpenAILLM

# コマンド引数
parser = argparse.ArgumentParser(description="TALK")
parser.add_argument("--obs_pass", type=str, required=True, help="OBS Websocketのパスワード")
parser.add_argument("--chat_video_id", type=str, required=True, help="YouTubeの動画ID")
args = parser.parse_args()

# obswebsocket
host = "127.0.0.1"
port = 4444
password = args.obs_pass
ws = obswebsocket.obsws(host, port, password)

# pytchat
chat = pytchat.create(video_id=args.chat_video_id)

# voicevox
speaker = 1  # ずんだもん

current_gpt_prefix_index = 0

with open("data/soliloquys.txt", encoding="utf8") as f:
    soliloquys = [line.strip() for line in f if len(line.strip()) > 1]


def obsTextChange(source_name: str, strtext: str):
    ws.call(
        obswebsocket.requests.SetSourceSettings(
            sourceName=source_name, sourceSettings={"text": strtext}
        )
    )


def init():
    OpenAILLM.init_openai()
    ws.connect()


def listen():
    if not chat.is_alive():
        print("ERROR: chat is dead.")
        time.sleep(0.1)
        exit()
    chats = [c for c in chat.get().sync_items() if len(c.message) <= 28]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


def think(author, prompt):
    global current_gpt_prefix_index

    if author == "furaga" and prompt == "あと少しの命です":
        current_gpt_prefix_index = 1
        print("Change current_gpt_prefix_index to", current_gpt_prefix_index)

    if author == "furaga" and prompt == "まだ大丈夫です":
        current_gpt_prefix_index = 0
        print("Change current_gpt_prefix_index to", current_gpt_prefix_index)

    # ハードコード
    if "初見" in prompt:
        return random.choice(
            [
                "初見は帰るのだ",
                "初見は帰れなのだ",
                "初見は帰れ",
                "帰れ",
            ]
        )

    # OpenAI APIで回答生成
    ret, response = OpenAILLM.ask_gpt(prompt)
    print(ret, response)
    if not ret:
        return ""
    return response["dialogue"]


def tts(text):
    # 音声合成
    res1 = requests.post(
        "http://127.0.0.1:50021/audio_query",
        params={"text": text, "speaker": speaker},
    )
    res2 = requests.post(
        "http://127.0.0.1:50021/synthesis",
        params={"speaker": speaker},
        data=json.dumps(res1.json()),
    )
    return res2.content


import asyncio


def fire_and_forget(func):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_in_executor(None, func, *args, *kwargs)

    return wrapper


speak_queue = []
stop_speak_thread = False


@fire_and_forget
def run_speak_thread():
    while True:
        if len(speak_queue) > 0:
            text, wav = speak_queue.pop(0)
            speak(text, wav)
        else:
            time.sleep(1)
        if stop_speak_thread:
            break


def request_speak(text, wav):
    speak_queue.append((text, wav))


def speak(text, wav):
    print("[speak]", text)

    # OBSの字幕変更
    obsTextChange("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


def main() -> None:
    init()

    run_speak_thread()

    prev_comment_time = time.time()
    while True:
        ret, author, prompt = listen()
        if not ret:
            if time.time() - prev_comment_time > 45:
                soliloquy = random.choice(soliloquys)
                print("soliloquy:", soliloquy)
                soliloquy_wav = tts(soliloquy)
                request_speak(soliloquy, soliloquy_wav)
                prev_comment_time = time.time()
            continue

        print("prompt:", prompt)

        answer = think(author, prompt)
        if len(answer) <= 0:
            answer = random.choice(
                [
                    "何を言っているかわからないのだ",
                    "訳のわからないことを言うななのだ",
                ]
            )
        print("answer:", answer)

        prompt_wav = tts(prompt)
        answer_wav = tts(answer)
        print("tts done")

        request_speak("「" + prompt + "」", prompt_wav)
        time.sleep(0.5)
        request_speak(answer, answer_wav)
        print("spoken")

        prev_comment_time = time.time()


if __name__ == "__main__":
    main()
