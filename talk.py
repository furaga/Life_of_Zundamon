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

from utils.asyncio_util import fire_and_forget
from utils import MK8DX
from utils import OpenAILLM
from utils import OBS


BOT_NAME = "ずんだもん"
talk_history_ = []
mk8dx_ = False

# pytchat
chat = None

# voicevox
speaker = 1  # ずんだもん

#
all_monologues = []


speak_queue = []
tts_queue_ = []
is_finish = False

mk8dx_history_ = []

latest_place = [0, "1"]

during_tts_ = False


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

    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask(question, talk_history_)
    print("[think]", ret, answer)
    if not ret:
        return random.choice(
            [
                "何を言っているかわからないのだ",
                "訳のわからないことを言うななのだ",
            ]
        )

    return "dialogue"


def think_mk8dx(n_coin, n_lap, omote, ura, place):
    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask_mk8dx(
        n_coin,
        n_lap,
        omote[1],
        ura[1],
        place[1],
        chat_history=[],
        race_mode=True,
    )
    answer = answer.replace("「", "").replace("」", "")
    if not ret:
        return ""
    return answer


# ランダムで流す独白
def think_monologues():
    return random.choice(all_monologues)


# 決め打ちのセリフ・処理
def play_scenario(author, question, mk8dx: bool):
    if mk8dx and author == "furaga" and question == "nf":
        # ゴールの感想を述べさせる
        _, answer = OpenAILLM.ask_mk8dx(
            0,
            0,
            None,
            None,
            latest_place[1],
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
def run_tts_loop():
    global is_finish
    while True:
        try:
            if len(tts_queue_) > 0:
                text = tts_queue_.pop(0)
                since = time.time()
                wav = tts(text)
                request_speak(text, wav)
                print(
                    f"[run_tts_thread] tts {text} | elapsed {time.time() - since:.2f} sec"
                )
            else:
                time.sleep(0.1)
            if is_finish:
                break
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            is_finish = True
            break


def tts(text):
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


def request_tts(speaker_name, text):
    global talk_history_
    talk_history_.append({"role": "system", "content": f"{speaker_name}: {text}"})
    if len(talk_history_) > 5:
        talk_history_ = talk_history_[-5:]
    tts_queue_.append(text)


#
# 音声再生
#
@fire_and_forget
def run_speak_loop():
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
                time.sleep(0.1)
            if is_finish:
                break
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            is_finish = True
            break


def speak(text, wav):
    # OBSの字幕変更
    OBS.set_text("zundamon_zimaku", text)

    # 音声再生
    play_obj = simpleaudio.play_buffer(wav, 1, 2, 24000)
    play_obj.wait_done()


def request_speak(text, wav):
    speak_queue.append((text, wav))


#
# マリカの画面を解析して実況させる
#
@fire_and_forget
def run_mk8dx_loop():
    global is_finish, latest_place
    with open("mk8dx_chat_history.txt", "a", encoding="utf8") as f:
        prev_lap = -1
        lap_start_time = time.time()
        while True:
            try:
                if is_finish:
                    break

                since = time.time()

                # ゲーム画面を解析
                img = OBS.capture_game_screen()
                ret, result = parse_mk8dx_screen(img)
                if not ret:
                    continue

                n_coin, n_lap, omote, ura, place = result
                if prev_lap != n_lap:
                    prev_lap = n_lap
                    lap_start_time = time.time()

                lap_position = "--"
                lap_position = "前半" if time.time() - lap_start_time < 20 else "後半"
                send_mk8dx_info_to_OBS(
                    n_coin, n_lap, omote, ura, place
                )  # , lap_position)

                #
                # TODO: いいかんじに
                #

                # 喋ることがないときにマリカの話をさせる
                if len(tts_queue_) >= 1 or len(speak_queue) >= 1:
                    continue

                # あまり昔すぎる情報を喋らせないように、ttsが終わってから返答を作り始める
                if during_tts_:
                    continue

                latest_place = place
                answer = think_mk8dx(
                    n_coin, n_lap, omote, ura, place
                )  # , lap_position)

                if len(answer) >= 1:
                    # 喋った内容を保存
                    f.write(f"{place},{omote},{ura},{n_lap},{n_coin},{answer}\n")
                    f.flush()

                    # ttsに流す
                    request_tts(BOT_NAME, answer)

                print(
                    f"[run_mk8dx] {answer} | elapsed {time.time() - since:.2f} sec",
                    flush=True,
                )
            except Exception as e:
                print(str(e), "\n", traceback.format_exc(), flush=True)
                is_finish = True
                break


def parse_mk8dx_screen(img):
    global mk8dx_history_

    # 画像解析
    ret_coin, n_coin = MK8DX.detect_coin(img)
    ret_lap, n_lap = MK8DX.detect_lap(img)
    omote, ura = MK8DX.detect_items(img)
    place = MK8DX.detect_place(img)
    finish = False

    # 画像マッチング系はしきい値を下回ったら無効
    # 裏アイテムは表がnoneなら絶対none (テレサは例外だけど・・・)
    if omote[0] < 0.81:
        omote = [0, "none"]
    if omote[1] == "none" or ura[0] < 0.7:
        ura = [0, "none"]
    if place[0] < 0.7:
        place = [0, "-1"]

    # OCR系は変な数値だったら無効
    if 0 <= n_coin <= 10:
        ret_coin = False
    if 0 <= n_lap <= 3:
        ret_lap = False

    # コイン・ラップが見えていたらレース中なはず
    is_racing = ret_coin and ret_lap  # and place[1] != "-1"

    if not is_racing:
        return False, None

    def same(a, b):
        for i in range(2):
            if a[i] != b[i]:
                return False

        for i in range(2, 5):
            if a[i][1] != b[i][1]:
                return False

        return True

    mk8dx_history_.append([n_coin, n_lap, omote, ura, place])
    if len(mk8dx_history_) >= 3:
        mk8dx_history_ = mk8dx_history_[-3:]

    if len(mk8dx_history_) < 3:
        return False, None

    # 3フレーム同じ結果だったら採用してOBS側を更新
    # TODO: 全部の要素の一致を見なくても良いのでは？個々の要素ごとに一致を見ればよいのでは
    for i in range(2):
        if same(mk8dx_history_[-1 - i :], mk8dx_history_[-2 - i :]):
            return False, None

    return True, mk8dx_history_[-1]


def send_mk8dx_info_to_OBS(n_coin, n_lap, omote, ura, place):
    text = f"順位: {place[1]}\n"
    text += f"アイテム: {omote[1]}, {ura[1]}\n"
    text += f"コイン: {n_coin}枚\n"
    text += f"ラップ: {n_lap}週目\n"
    OBS.set_text("current_mk8dx_info", text)


#
# Youtubeのチャットからコメントを拾って回答するボットを動かす
#
@fire_and_forget
def run_chatbot_loop():
    global is_finish

    prev_listen_time = time.time()
    while True:
        try:
            # Youtubeの最新のコメントを拾う
            ret, author, question = youtube_listen_chat()

            # 一定時間なにもコメントがなかったら独白
            if not ret and not mk8dx_ and time.time() - prev_listen_time > 45:
                monologue = think_monologues()
                request_tts(BOT_NAME, monologue)
                prev_listen_time = time.time()
                continue

            # コメントがなかったら、もう一度ループ
            if not ret:
                prev_listen_time = time.time()
                continue

            # 特定ワードで決め打ちの処理を行う
            talked_any = play_scenario(author, question, mk8dx_)
            if talked_any:
                prev_listen_time = time.time()
                continue

            # 質問文を読み上げる
            request_tts("User", "「" + question + "」")

            # 回答を考える
            answer = think(author, question)

            # 回答を読み上げる
            request_tts(BOT_NAME, answer)

            prev_listen_time = time.time()
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            is_finish = True
            break


# YouTubeのコメント欄の最新のチャットを取得する
def youtube_listen_chat():
    global is_finish
    if not chat.is_alive():
        # TODO: ちゃんとした対応？
        print("[listen] ERROR: chat is dead.")
        is_finish = True
        time.sleep(0.1)
        exit()
    # 40文字以内のコメントのみ取得（長文コメントは無視）
    chats = [c for c in chat.get().sync_items() if len(c.message) <= 40]
    if len(chats) <= 0:
        return False, "", ""
    return True, chats[-1].author.name, chats[-1].message


#
# 初期化
#


def init(args):
    global chat

    # youtube
    chat = pytchat.create(video_id=args.chat_video_id)

    # openai
    OpenAILLM.init("data/config/mk8dx/prompt.json")

    # obs
    OBS.init(args.obs_pass)

    # mk8dx
    mk8dx_ = args.mk8dx
    if mk8dx_:
        MK8DX.init(Path("data/mk8dx_images"))

    # monologue
    global all_monologues
    with open("data/soliloquys.txt", encoding="utf8") as f:
        all_monologues = [line.strip() for line in f if len(line.strip()) > 1]


def reset_mk8dx():
    global mk8dx_history_
    mk8dx_history_ = []
    OBS.set_text("zundamon_zimaku", "")
    send_mk8dx_info_to_OBS(0, 0, [1, "--"], [1, "--"], [1, "--"])


async def main(args) -> None:
    # 初期化
    init(args)

    # 並行処理を起動
    run_chatbot_loop()
    run_tts_loop()
    run_speak_loop()
    if args.mk8dx:
        run_mk8dx_loop()

    # メインループは何もしない（ヘルスチェックくらいする？)
    while True:
        if is_finish:
            break
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
