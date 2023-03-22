import requests
import pytchat
import obswebsocket
import time
import json
import simpleaudio
import random
import argparse
import queue

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
    global stop_speak_thread
    if not chat.is_alive():
        print("[listen] ERROR: chat is dead.")
        stop_speak_thread = True
        time.sleep(0.1)
        exit()
    chats = [c for c in chat.get().sync_items() if len(c.message) <= 28]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


def think(author, prompt, chat_history):
    global current_gpt_prefix_index
    print("[think] BBB", flush=True)

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
    print("[think] AAA", flush=True)
    ret, response = OpenAILLM.ask_gpt(prompt, chat_history)
    print("[think]", ret, response)
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


speak_queue = queue.Queue()
stop_speak_thread = False


@fire_and_forget
def run_speak_thread():
    while True:
        text, wav = speak_queue.get()
        print(f"[run_speak_thread] pop {text}")
        since = time.time()
        speak(text, wav)
        print(
            f"[run_speak_thread] spoken {text} | elapsed {time.time() - since:.2f} sec"
        )
        speak_queue.task_done()
        if stop_speak_thread:
            break


def request_speak(text, wav):
    speak_queue.put((text, wav))


def speak(text, wav):
    # OBSの字幕変更
    obsTextChange("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


prev_comment_time = time.time()
chat_history = []


@fire_and_forget
def run_listen_think_thread(author, prompt):
    global prev_comment_time
    print("[run_listen_think_thread] run_listen_think_thread", flush=True)

    answer = think(author, prompt, chat_history)
    if len(answer) <= 0:
        answer = random.choice(
            [
                "何を言っているかわからないのだ",
                "訳のわからないことを言うななのだ",
            ]
        )
    print(
        "[run_listen_think_thread] think:",
        answer,
        f"| elapsed {time.time() - since:.2f} sec",
        flush=True,
    )
    since = time.time()

    prompt_wav = tts(prompt)
    print(
        "[run_listen_think_thread] tts1",
        f"| elapsed {time.time() - since:.2f} sec",
        flush=True,
    )
    since = time.time()

    request_speak("「" + prompt + "」", prompt_wav)
    print(
        "[run_listen_think_thread] request_speak1",
        prompt,
        f"| elapsed {time.time() - since:.2f} sec",
        flush=True,
    )
    since = time.time()

    answer_wav = tts(answer)
    print(
        "[run_listen_think_thread] tts2",
        f"| elapsed {time.time() - since:.2f} sec",
        flush=True,
    )
    since = time.time()

    request_speak(answer, answer_wav)
    print(
        "[run_listen_think_thread] request_speak2",
        answer,
        f"| elapsed {time.time() - since:.2f} sec",
        flush=True,
    )

    chat_history.append({"role": "system", "content": "User: " + prompt})
    chat_history.append({"role": "system", "content": "ずんだもん: " + answer})
    if len(chat_history) > 5:
        chat_history = chat_history[-5:]

    prev_comment_time = time.time()


async def main() -> None:
    global prev_comment_time

    init()

    run_listen_think_thread()
    run_speak_thread()

    while True:
        since = time.time()
        ret, author, prompt = listen()
        if not ret:
            if time.time() - prev_comment_time > 45:
                soliloquy = random.choice(soliloquys)
                print("[main] soliloquy:", soliloquy)
                soliloquy_wav = tts(soliloquy)
                request_speak(soliloquy, soliloquy_wav)
                prev_comment_time = time.time()
            continue

        print("[main] listen:", prompt, f"| elapsed {time.time() - since:.2f} sec")
        since = time.time()

        run_listen_think_thread(author, prompt)

        print(
            "[main] run_listen_think_thread:",
            prompt,
            f"| elapsed {time.time() - since:.2f} sec",
        )
        await asyncio.sleep(1)

    # prev_comment_time = time.time()
    # chat_history = []

    # while True:
    #     since = time.time()
    #     ret, author, prompt = listen()
    #     if not ret:
    #         if time.time() - prev_comment_time > 45:
    #             soliloquy = random.choice(soliloquys)
    #             print("[main] soliloquy:", soliloquy)
    #             soliloquy_wav = tts(soliloquy)
    #             request_speak(soliloquy, soliloquy_wav)
    #             prev_comment_time = time.time()
    #         continue

    #     print("[main] listen:", prompt, f"| elapsed {time.time() - since:.2f} sec")
    #     since = time.time()

    #     answer = think(author, prompt, chat_history)
    #     if len(answer) <= 0:
    #         answer = random.choice(
    #             [
    #                 "何を言っているかわからないのだ",
    #                 "訳のわからないことを言うななのだ",
    #             ]
    #         )
    #     print("[main] think:", answer, f"| elapsed {time.time() - since:.2f} sec")
    #     since = time.time()

    #     prompt_wav = tts(prompt)
    #     print("[main] tts1", f"| elapsed {time.time() - since:.2f} sec")
    #     since = time.time()

    #     request_speak("「" + prompt + "」", prompt_wav)
    #     print(
    #         "[main] request_speak1", prompt, f"| elapsed {time.time() - since:.2f} sec"
    #     )
    #     since = time.time()

    #     answer_wav = tts(answer)
    #     print("[main] tts2", f"| elapsed {time.time() - since:.2f} sec")
    #     since = time.time()

    #     request_speak(answer, answer_wav)
    #     print(
    #         "[main] request_speak2", answer, f"| elapsed {time.time() - since:.2f} sec"
    #     )

    #     chat_history.append({"role": "system", "content": "User: " + prompt})
    #     chat_history.append({"role": "system", "content": "ずんだもん: " + answer})
    #     if len(chat_history) > 5:
    #         chat_history = chat_history[-5:]

    #     prev_comment_time = time.time()


if __name__ == "__main__":
    asyncio.run(main())
