import requests
import pytchat
import obswebsocket
import time
import json
import simpleaudio
import random
import argparse
import os
from pathlib import Path
import cv2

from utils import MK8DX
from utils import OpenAILLM

# コマンド引数
parser = argparse.ArgumentParser(description="TALK")
parser.add_argument("--obs_pass", type=str, required=True, help="OBS Websocketのパスワード")
parser.add_argument("--chat_video_id", type=str, required=True, help="YouTubeの動画ID")
parser.add_argument("--mk8dx", action="store_true")
args = parser.parse_args()

# obswebsocket
host = "localhost"
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
    global is_finish
    if not chat.is_alive():
        print("[listen] ERROR: chat is dead.")
        is_finish = True
        time.sleep(0.1)
        exit()
    chats = [c for c in chat.get().sync_items() if len(c.message) <= 40]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


def think(author, prompt, chat_history):
    global current_gpt_prefix_index

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


speak_queue = []
tts_queue = []
is_finish = False


@fire_and_forget
def run_speak_thread():
    global is_finish
    while True:
        try:
            if len(speak_queue) > 0:
                text, wav = speak_queue.pop(0)
                print(f"[run_speak_thread] pop {text}")
                since = time.time()
                speak(text, wav)
                print(
                    f"[run_speak_thread] spoken {text} | elapsed {time.time() - since:.2f} sec"
                )
            else:
                time.sleep(0.5)
            if is_finish:
                break
        except Exception as e:
            import traceback

            print("error in run_speak_thread:", e)
            print(traceback.format_exc())
            is_finish = True
            break


def game_capture():
    out_path = Path(os.getcwd()) / "__tmp__.jpg"
    ws.call(
        obswebsocket.requests.TakeSourceScreenshot(
            sourceName="映像キャプチャデバイス",
            embedPictureFormat="jpg",
            saveToFilePath=str(out_path).replace("\\", "/"),
        )
    )
    img = cv2.imread(str(out_path))
    return img


mk8dx_history = []


def parse_mk8dx_screen(img):
    global mk8dx_history
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

    mk8dx_history.append([n_coin, n_lap, omote, ura, place])

    if not ret_coin or not (0 <= n_coin <= 10):
        return False, None
    if not ret_lap or not (0 <= n_lap <= 3):
        return False, None
    if place[1] == "-1":
        return False, None

    # print(f"[C] Elapsed {time.time() - since:.2f} sec")
    # since = time.time()

    if len(mk8dx_history) >= 3:
        mk8dx_history = mk8dx_history[-3:]

    if len(mk8dx_history) < 3:
        return False, None

    def is_same_history_item(a, b):
        for i in range(2):
            if a[i] != b[i]:
                return False

        for i in range(2, 5):
            if a[i][1] != b[i][1]:
                return False

        return True

    # 3フレーム同じ結果だったら採用してOBS側を更新
    if not is_same_history_item(mk8dx_history[-1], mk8dx_history[-2]):
        return False, None
    if not is_same_history_item(mk8dx_history[-2], mk8dx_history[-3]):
        return False, None

    return True, (n_coin, n_lap, omote, ura, place)


def think_mk8dx(n_coin, n_lap, omote, ura, place):
    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask_gpt_mk8dx(n_coin, n_lap, omote[1], ura[1], place[1])
    answer = answer.replace("「", "").replace("」", "")
    if not ret:
        return ""
    return answer


def set_obs_current_mk8dx_info(n_coin, n_lap, omote, ura, place):
    text = f"順位: {place[1]}\n"
    text += f"アイテム: {omote[1]}, {ura[1]}\n"
    text += f"コイン: {n_coin}枚\n"
    text += f"ラップ: {n_lap}週目\n"
    obsTextChange("current_mk8dx_info", text)


latest_place = [0, "1"]


@fire_and_forget
def run_mk8dx():
    global is_finish, latest_place
    MK8DX.init(Path("data/mk8dx_images"))
    set_obs_current_mk8dx_info(0, 0, [1, "--"], [1, "--"], [1, "--"])
    with open("mk8dx_chat_history.txt", "a", encoding="utf8") as f:
        while True:
            try:
                if is_finish:
                    break

                since = time.time()
                # print("[run_mk8dx] start game capture", flush=True)
                img = game_capture()
                # print("[run_mk8dx] game capture", flush=True)
                ret, result = parse_mk8dx_screen(img)
                # print("[run_mk8dx] parse_mk8dx_screen", flush=True)
                if not ret:
                    continue

                n_coin, n_lap, omote, ura, place = result
                set_obs_current_mk8dx_info(n_coin, n_lap, omote, ura, place)
                # print("[run_mk8dx] set_obs_current_mk8dx_info", flush=True)

                # 喋ることがないときにマリカの話をさせる
                if len(tts_queue) >= 1 or len(speak_queue) >= 1:
                    continue

                latest_place = place
                answer = think_mk8dx(n_coin, n_lap, omote, ura, place)
                # print("[run_mk8dx] think_mk8dx")
                if len(answer) >= 1:
                    f.write(f"{place},{omote},{ura},{n_lap},{n_coin},{answer}\n")
                    f.flush()
                    request_tts(answer)
                print(
                    "[run_mk8dx] think:",
                    answer,
                    f"| elapsed {time.time() - since:.2f} sec",
                    flush=True,
                )
            except Exception as e:
                import traceback

                print("error in run_mk8dx:", e)
                print(traceback.format_exc())
                is_finish = True
                break


def request_speak(text, wav):
    speak_queue.append((text, wav))


@fire_and_forget
def run_tts_thread():
    global is_finish
    while True:
        try:
            if len(tts_queue) > 0:
                text = tts_queue.pop(0)
                since = time.time()
                wav = tts(text)
                request_speak(text, wav)
                print(
                    f"[run_tts_thread] tts {text} | elapsed {time.time() - since:.2f} sec"
                )
            else:
                time.sleep(0.5)
            if is_finish:
                break
        except Exception as e:
            import traceback

            print("error in run_tts_thread:", e)
            print(traceback.format_exc())
            is_finish = True
            break


def request_tts(text):
    tts_queue.append(text)


def speak(text, wav):
    # OBSの字幕変更
    obsTextChange("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


async def main() -> None:
    global is_finish

    init()
    obsTextChange("zundamon_zimaku", "")

    run_tts_thread()
    run_speak_thread()

    if args.mk8dx:
        run_mk8dx()

    prev_comment_time = time.time()
    chat_history = []

    while True:
        try:
            since = time.time()
            ret, author, prompt = listen()
            if not ret:
                if not args.mk8dx:
                    if time.time() - prev_comment_time > 45:
                        soliloquy = random.choice(soliloquys)
                        print("[main] soliloquy:", soliloquy)
                        soliloquy_wav = tts(soliloquy)
                        request_speak(soliloquy, soliloquy_wav)
                        prev_comment_time = time.time()
                continue

            if args.mk8dx and author == "furaga" and prompt == "nf":
                # ゴールの感想を述べさせる
                _, answer = OpenAILLM.ask_gpt_mk8dx(
                    0, 0, None, None, latest_place[1], nf=True
                )
                request_tts(answer)
                print(
                    "[main] think:", answer, f"| elapsed {time.time() - since:.2f} sec"
                )
                prev_comment_time = time.time()
            elif args.mk8dx and author == "furaga" and prompt == "こんばんは":
                # 開始の挨拶
                request_tts("ずんだもんなのだ。今日はマリオカートをやっていくのだ")
                request_tts("ずんだもんはあまりマリカが上手じゃないけれど、頑張ってプレイするのだ")
                request_tts("さっそく始めるのだ")
                prev_comment_time = time.time()
            elif args.mk8dx and author == "furaga" and prompt == "そろそろ":
                # 終わりの挨拶
                request_tts("今日はこのへんで終わりにするのだ。楽しかったのだ")
                request_tts("見てくれたみんなもありがとうなのだ")
                request_tts("よかったらチャンネル登録と高評価お願いしますなのだ")
                request_tts("次回の配信もぜひ見に来てほしいのだ")
                request_tts("じゃあ、お疲れ様でした、なのだ！")
                prev_comment_time = time.time()
            else:
                since = time.time()
                request_tts("「" + prompt + "」")
                print(
                    "[main] listen:", prompt, f"| elapsed {time.time() - since:.2f} sec"
                )
                answer = think(author, prompt, chat_history)

                if len(answer) <= 0:
                    answer = random.choice(
                        [
                            "何を言っているかわからないのだ",
                            "訳のわからないことを言うななのだ",
                        ]
                    )
                request_tts(answer)
                print(
                    "[main] think:", answer, f"| elapsed {time.time() - since:.2f} sec"
                )
                since = time.time()

                chat_history.append({"role": "system", "content": "User: " + prompt})
                chat_history.append({"role": "system", "content": "ずんだもん: " + answer})
                if len(chat_history) > 5:
                    chat_history = chat_history[-5:]

                prev_comment_time = time.time()
        except Exception as e:
            import traceback

            print("error in run_tts_thread:", e)
            print(traceback.format_exc())
            is_finish = True
            break


if __name__ == "__main__":
    asyncio.run(main())
