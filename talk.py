import asyncio
import requests
import pytchat
import time
import json
import simpleaudio
import random
import argparse
from pathlib import Path
import traceback
import threading

from utils.asyncio_util import fire_and_forget
from utils import MK8DX
from utils import OpenAILLM
from utils import OBS


BOT_NAME = "ずんだもん"
talk_history_ = []
is_mk8dx_mode_ = False

# pytchat
youtube_chat_ = None

# voicevox
speaker_ = 1  # ずんだもん

#
all_monologues_ = []


speak_queue_ = []
mk8dx_speak_queue_ = []
tts_queue_ = []
app_done_ = False

mk8dx_raw_status_history_ = []
mk8dx_status_history_ = []
mk8dx_status_updated_ = False


latest_place_ = [0, "1"]

during_tts_ = False

locks_ = {}


def get_lock(name):
    if name not in locks_:
        locks_[name] = threading.Lock()
    return locks_[name]


# コマンド引数
def parse_args():
    parser = argparse.ArgumentParser(description="TALK")
    parser.add_argument(
        "--obs_pass", type=str, required=True, help="OBS Websocketのパスワード"
    )
    parser.add_argument("--chat_video_id", type=str, required=True, help="YouTubeの動画ID")
    parser.add_argument("--mk8dx", action="store_true")
    args = parser.parse_args()
    return args


#
# think: ずんだもんのセリフを考える
#


# チャットへの回答を考える
def think(author, question):
    # ハードコード
    if "初見" in question:
        return random.choice(
            [
                "初見は帰るのだ",
                "初見は帰れなのだ",
                "初見は帰れ",
                "帰れ",
            ]
        )

    with get_lock("talk_history"):
        history = talk_history_.copy()

    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask(question, history)
    print("[think]", ret, answer)
    if not ret:
        return random.choice(
            [
                "何を言っているかわからないのだ",
                "訳のわからないことを言うななのだ",
            ]
        )

    return "dialogue"


def think_mk8dx(n_coin, n_lap, lap_time, omote, ura, place, delta_coin):
    # TODO: lap_time, delta_coinを使う
    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask_mk8dx(
        n_coin,
        n_lap,
        lap_time,
        omote[1],
        ura[1],
        place[1],
        delta_coin,
        chat_history=[],
        is_race_mode=True,
    )
    answer = answer.replace("「", "").replace("」", "")
    if not ret:
        return ""
    return answer


# ランダムで流す独白
def think_monologues():
    return random.choice(all_monologues_)


# 決め打ちのセリフ・処理
def play_scenario(author, question, mk8dx: bool):
    if mk8dx and author == "furaga" and question == "nf":
        # ゴールの感想を述べさせる
        _, answer = OpenAILLM.ask_mk8dx(
            0,
            0,
            None,
            None,
            latest_place_[1],
            chat_history=[],
            race_mode=False,
        )
        request_tts(BOT_NAME, answer)
        reset_mk8dx()
        return True
    elif mk8dx and author == "furaga" and question == "こんばんは":
        # 開始の挨拶
        request_tts(BOT_NAME, "ずんだもんなのだ。今日もマリオカートをやっていくのだ")
        request_tts(BOT_NAME, "まだまだ上手ではないけれど、一生懸命プレイするのだ。みんなも楽しんでほしいのだ")
        request_tts(BOT_NAME, "コメントもどんどんしてほしいのだ。よろしくなのだ")
        request_tts(BOT_NAME, "さっそく始めるのだ")
        return True
    elif mk8dx and author == "furaga" and question == "そろそろ":
        # 終わりの挨拶
        request_tts(BOT_NAME, "今日はこのへんで終わりにするのだ。楽しかったのだ")
        request_tts(BOT_NAME, "見てくれたみんなもありがとうなのだ")
        request_tts(BOT_NAME, "よかったらチャンネル登録と高評価お願いしますなのだ")
        request_tts(BOT_NAME, "次回の配信もぜひ見に来てほしいのだ")
        request_tts(BOT_NAME, "じゃあ、お疲れ様でした、なのだ！")
        return True

    return False


#
# TTS (Text To Speech)
#
@fire_and_forget
def run_tts_thread():
    global app_done_
    while not app_done_:
        try:
            text = ""
            with get_lock("tts_queue"):
                if len(tts_queue_) > 0:
                    text = tts_queue_.pop(0)
            if len(text) > 0:
                since = time.time()
                wav = tts(text)
                request_speak(text, wav)
                print(
                    f"[run_tts_thread] tts {text} | elapsed {time.time() - since:.2f} sec"
                )
            time.sleep(0.1)
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            app_done_ = True
            break


def tts(text):
    res1 = requests.post(
        "http://127.0.0.1:50021/audio_query",
        params={"text": text, "speaker": speaker_},
    )
    res2 = requests.post(
        "http://127.0.0.1:50021/synthesis",
        params={"speaker": speaker_},
        data=json.dumps(res1.json()),
    )
    return res2.content


def request_tts(speaker_name, text):
    global talk_history_
    with get_lock("talk_history"):
        talk_history_.append({"role": "system", "content": f"{speaker_name}: {text}"})
        if len(talk_history_) > 5:
            talk_history_ = talk_history_[-5:]

    with get_lock("tts_queue"):
        tts_queue_.append(text)


#
# 音声再生
#
@fire_and_forget
def run_speak_thread():
    global app_done_
    while not app_done_:
        try:
            # 通常
            text, wav = "", None
            print("[run_speak_thread] A", flush=True)
            with get_lock("speak_queue"):
                if len(speak_queue_) > 0:
                    text, wav = speak_queue_.pop(0)

            if len(text) > 0:
                since = time.time()
                speak(text, wav)
                print(
                    f"[run_speak_thread] {text} | elapsed {time.time() - since:.2f} sec"
                )

            # マリオカート用
            print("[run_speak_thread] B", flush=True)
            text, wav = "", None
            with get_lock("mk8dx_speak_queue"):
                if len(mk8dx_speak_queue_) > 0:
                    text, wav = mk8dx_speak_queue_.pop(0)

            if len(text) > 0:
                since = time.time()
                speak(text, wav)
                print(
                    f"[run_speak_thread(mk8dx)] {text} | elapsed {time.time() - since:.2f} sec"
                )

            print("[run_speak_thread] C", flush=True)
            time.sleep(0.1)

        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            app_done_ = True
            break


def speak(text, wav):
    # OBSの字幕変更
    OBS.set_text("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


def request_speak(text, wav):
    with get_lock("speak_queue"):
        speak_queue_.append((text, wav))


def request_mk8dx_speak(text, wav):
    with get_lock("mk8dx_speak_queue"):
        mk8dx_speak_queue_.append((text, wav))


def cancel_mk8dx_speak():
    with get_lock("mk8dx_speak_queue"):
        mk8dx_speak_queue_.clear()


#
# マリカの画面を解析して実況させる
#

is_finished_screen_ = False


@fire_and_forget
def run_mk8dx_game_capture_thread():
    print("[run_mk8dx_game_capture_thread] Start")
    global app_done_, mk8dx_status_history_, mk8dx_status_updated_, is_finished_screen_
    with open("mk8dx_chat_history.txt", "a", encoding="utf8") as f:
        prev_lap = -1
        lap_start_time = time.time()
        last_finished_time = 0
        while not app_done_:
            try:
                since = time.time()

                # ゲーム画面を解析
                img = OBS.capture_game_screen()
                ret, parse_result, is_finished = parse_mk8dx_screen(img)

                # "FINISH"の文字が出たら5秒間くらい何もしゃべらないモードにしたい
                if is_finished:
                    is_finished_screen_ = True
                    last_finished_time = time.time()
                elif time.time() - last_finished_time > 15:
                    is_finished_screen_ = False

                send_mk8dx_finished_to_OBS(is_finished_screen_)
                if not ret:
                    time.sleep(0.1)
                    continue

                n_coin, n_lap, omote, ura, place = parse_result
                if prev_lap != n_lap:
                    prev_lap = n_lap
                    lap_start_time = time.time()
                lap_time = time.time() - lap_start_time

                status = n_coin, n_lap, lap_time, omote, ura, place
                send_mk8dx_status_to_OBS(*status)

                with get_lock("mk8dx_status"):
                    mk8dx_status_history_.append(status)
                    if len(mk8dx_status_history_) > 2:
                        # とりあえず今と直前の2要素だけあればよい
                        mk8dx_status_history_ = mk8dx_status_history_[-2:]
                    mk8dx_status_updated_ = True

                print(
                    f"[run_mk8dx_game_capture_thread] Elapsed {time.time() - since:.2f} sec"
                )

                time.sleep(0.1)
            except Exception as e:
                print(str(e), "\n", traceback.format_exc(), flush=True)
                app_done_ = True
                break


@fire_and_forget
def run_mk8dx_think_tts_thread():
    global app_done_, latest_place_, mk8dx_status_updated_
    print("[run_mk8dx_think_tts_thread] Start")
    with open("mk8dx_chat_history.txt", "a", encoding="utf8") as f:
        while not app_done_:
            try:
                since = time.time()

                prev_status, cur_status = None, None
                with get_lock("mk8dx_status"):
                    if mk8dx_status_updated_:
                        if len(mk8dx_status_history_) >= 2:
                            prev_status = mk8dx_status_history_[-2]
                        if len(mk8dx_status_history_) >= 1:
                            cur_status = mk8dx_status_history_[-1]
                        mk8dx_status_updated_ = False

                # フィニッシュ画面は黙る
                if is_finished_screen_:
                    cancel_mk8dx_speak()
                    time.sleep(0.1)
                    continue

                # 更新ないのでスキップ
                if cur_status is None:
                    time.sleep(0.1)
                    continue

                n_coin, n_lap, lap_time, omote, ura, place = cur_status
                delta_coin = (
                    cur_status[0] - prev_status[0] if prev_status is not None else 0
                )

                latest_place_ = place
                answer = think_mk8dx(
                    n_coin, n_lap, lap_time, omote, ura, place, delta_coin
                )

                if len(answer) >= 1:
                    # 喋った内容を保存
                    f.write(f"{place},{omote},{ura},{n_lap},{n_coin},{answer}\n")
                    f.flush()

                    # tts（時間に余裕があるので同期）
                    global talk_history_
                    with get_lock("talk_history"):
                        talk_history_.append(
                            {"role": "system", "content": f"{BOT_NAME}: {answer}"}
                        )
                        if len(talk_history_) > 5:
                            talk_history_ = talk_history_[-5:]

                    wav = tts(answer)

                    # 再生（非同期）
                    request_mk8dx_speak(answer, wav)

                print(
                    f"[run_mk8dx] {answer} | elapsed {time.time() - since:.2f} sec",
                    flush=True,
                )
                time.sleep(0.1)
            except Exception as e:
                print(str(e), "\n", traceback.format_exc(), flush=True)
                app_done_ = True
                break


def parse_mk8dx_screen(img):
    global mk8dx_raw_status_history_

    # 画像解析
    ret_coin, n_coin = MK8DX.detect_coin(img)
    ret_lap, n_lap = MK8DX.detect_lap(img)
    omote, ura = MK8DX.detect_items(img)
    place = MK8DX.detect_place(img)

    finish = MK8DX.detect_finish(img)
    is_finished = finish[0] > 0.95 and finish[1] == "finish"

    # 画像マッチング系はしきい値を下回ったら無効
    # 裏アイテムは表がnoneなら絶対none (テレサは例外だけど・・・)
    if omote[0] < 0.81:
        omote = [0, "none"]
    if omote[1] == "none" or ura[0] < 0.7:
        ura = [0, "none"]
    if place[0] < 0.7:
        place = [0, "-1"]

    # OCR系は変な数値だったら無効
    if not (0 <= n_coin <= 10):
        ret_coin = False
    if not (0 <= n_lap <= 3):
        ret_lap = False

    # コイン・ラップが見えていたらレース中なはず
    is_racing = ret_coin and ret_lap  # and place[1] != "-1"

    if not is_racing:
        return False, None, is_finished

    def same(a, b):
        # print("[same]", a, b)
        for i in range(2):
            if a[i] != b[i]:
                return False

        for i in range(2, 5):
            if a[i][1] != b[i][1]:
                return False

        return True

    mk8dx_raw_status_history_.append([n_coin, n_lap, omote, ura, place])
    if len(mk8dx_raw_status_history_) >= 3:
        mk8dx_raw_status_history_ = mk8dx_raw_status_history_[-3:]

    if len(mk8dx_raw_status_history_) < 3:
        return False, None, is_finished

    # 3フレーム同じ結果だったら採用してOBS側を更新
    # TODO: 全部の要素の一致を見なくても良いのでは？個々の要素ごとに一致を見ればよいのでは
    for i in range(2):
        if not same(
            mk8dx_raw_status_history_[-1 - i], mk8dx_raw_status_history_[-2 - i]
        ):
            # print("B")
            return False, None, is_finished

    return True, mk8dx_raw_status_history_[-1], is_finished


def send_mk8dx_status_to_OBS(n_coin, n_lap, lap_time, omote, ura, place):
    text = f"順位: {place[1]}\n"
    text += f"アイテム: {omote[1]}, {ura[1]}\n"
    text += f"コイン: {n_coin}枚\n"
    text += f"ラップ: {n_lap}週目 ({lap_time:.1f}秒)\n"
    OBS.set_text("mk8dx_status", text)


def send_mk8dx_finished_to_OBS(is_finish_screen):
    if is_finish_screen:
        text = f"FINISHED"
    else:
        text = f""
    OBS.set_text("mk8dx_status_finish", text)


#
# Youtubeのチャットからコメントを拾って回答するボットを動かす
#
@fire_and_forget
def run_chatbot_thread():
    print("[run_chatbot_thread] Start")
    global app_done_

    prev_listen_time = time.time()
    while not app_done_:
        try:
            # Youtubeの最新のコメントを拾う
            ret, author, question = youtube_listen_chat()

            # 一定時間なにもコメントがなかったら独白
            if not ret and not is_mk8dx_mode_ and time.time() - prev_listen_time > 45:
                monologue = think_monologues()
                request_tts(BOT_NAME, monologue)
                prev_listen_time = time.time()
                time.sleep(0.1)
                continue

            # コメントがなかったら、もう一度ループ
            if not ret:
                prev_listen_time = time.time()
                time.sleep(0.1)
                continue

            # 特定ワードで決め打ちの処理を行う
            talked_any = play_scenario(author, question, is_mk8dx_mode_)
            if talked_any:
                prev_listen_time = time.time()
                time.sleep(0.1)
                continue

            # 質問文を読み上げる
            request_tts("User", "「" + question + "」")

            # 回答を考える
            answer = think(author, question)

            # 回答を読み上げる
            request_tts(BOT_NAME, answer)

            prev_listen_time = time.time()
            time.sleep(0.1)
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            app_done_ = True
            break


# YouTubeのコメント欄の最新のチャットを取得する
def youtube_listen_chat():
    global app_done_
    if not youtube_chat_.is_alive():
        # TODO: ちゃんとした対応？
        print("[listen] ERROR: chat is dead.")
        app_done_ = True
        time.sleep(0.1)
        exit()
    # 40文字以内のコメントのみ取得（長文コメントは無視）
    chats = [c for c in youtube_chat_.get().sync_items() if len(c.message) <= 40]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


#
# 初期化
#


def init(args):
    global youtube_chat_

    # youtube
    youtube_chat_ = pytchat.create(video_id=args.chat_video_id)

    # openai
    OpenAILLM.init(Path("data/config/mk8dx/prompt.json"))

    # obs
    OBS.init(args.obs_pass)

    # mk8dx
    mk8dx_ = args.mk8dx
    if mk8dx_:
        MK8DX.init(Path("data/mk8dx_images"))
        reset_mk8dx()

    # monologue
    global all_monologues_
    with open("data/soliloquys.txt", encoding="utf8") as f:
        all_monologues_ = [line.strip() for line in f if len(line.strip()) > 1]


def reset_mk8dx():
    global mk8dx_raw_status_history_, mk8dx_status_history_, mk8dx_status_updated_, is_finished_screen_
    with get_lock("mk8dx_history"):
        mk8dx_raw_status_history_ = []
        mk8dx_status_history_ = []
        mk8dx_status_updated_ = False
        is_finished_screen_ = False
    OBS.set_text("zundamon_zimaku", "")
    send_mk8dx_status_to_OBS(0, 0, 0, [1, "--"], [1, "--"], [1, "--"])
    send_mk8dx_finished_to_OBS(False)


async def main(args) -> None:
    # 初期化
    init(args)

    # 並行処理を起動
    run_chatbot_thread()
    run_tts_thread()
    run_speak_thread()
    if args.mk8dx:
        run_mk8dx_game_capture_thread()
        run_mk8dx_think_tts_thread()

    # メインループは何もしない（ヘルスチェックくらいする？)
    while True:
        if app_done_:
            break
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
