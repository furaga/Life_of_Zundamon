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

#
all_monologues_ = []


speak_queue_ = []
mk8dx_speak_queue_ = []
tts_queue_ = []
app_done_ = False

mk8dx_raw_history_ = []
mk8dx_status_history_ = []
mk8dx_status_updated_ = False
mk8dx_spoken_result_ = False

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
    # # ハードコード
    # if "初見" in question:
    #     return random.choice(
    #         [
    #             "初見は帰るのだ",
    #             "初見は帰れなのだ",
    #             "初見は帰れ",
    #             "帰れ",
    #         ]
    #     )

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

    return answer


def think_mk8dx_reaction():
    # ランダムな被弾セリフを流す
    answer = random.choice(damage_voices)
    print("[think_mk8dx_reaction]", answer)
    return answer, "mk8dx_reaction"


def think_mk8dx(status):
    # OpenAI APIで回答生成
    ret, answer = OpenAILLM.ask_mk8dx(
        status.n_coin,
        status.n_lap,
        status.lap_time,
        status.item_omote,
        status.item_ura,
        status.place,
        0,
        chat_history=[],
        is_race_mode=True,
    )
    answer = answer.replace("「", "").replace("」", "")
    if not ret:
        return "", ""
    return answer, "mk8dx"


# ランダムで流す独白
def think_monologues():
    return random.choice(all_monologues_)


# 決め打ちのセリフ・処理
def play_scenario(author, question, mk8dx: bool):
    global mk8dx_spoken_result_
    if mk8dx and author == "furaga" and question == "nf":
        # リセットだけさせたい
        print(">[play_scenario] nf", flush=True)
        reset_mk8dx()
        return True
    elif mk8dx_game_state_ == "FINISH":
        # ゴールの感想を言わせたい
        if mk8dx_spoken_result_:
            return False

        print(">[play_scenario] 感想", flush=True)
        mk8dx_spoken_result_ = True

        # OpenAI APIで回答生成
        ret, answer = OpenAILLM.ask_mk8dx(
            0,
            0,
            0,
            "",
            "",
            latest_place_[1],
            0,
            chat_history=[],
            is_race_mode=False,
        )
        if not ret:
            return False

        request_tts(BOT_NAME, answer)
        print(">[play_scenario]", answer, flush=True)

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
                    text, speed = tts_queue_.pop(0)
            if len(text) > 0:
                since = time.time()
                wav = tts(text, speed)
                request_speak(text, wav)
                print(
                    f"[run_tts_thread] tts {text} | elapsed {time.time() - since:.2f} sec"
                )
            time.sleep(0.1)
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            app_done_ = True
            break


def tts(text, speed=1.1, speaker=3):
    if text in tts_cache_:
        return tts_cache_[text]

    with get_lock("tts"):
        res1 = requests.post(
            "http://127.0.0.1:50021/audio_query",
            params={"text": text, "speaker": speaker},
        )
        data = res1.json()
        data["speedScale"] = speed
        res2 = requests.post(
            "http://127.0.0.1:50021/synthesis",
            params={"speaker": speaker},
            data=json.dumps(data),
        )
    return res2.content


def request_tts(speaker_name, text, speed=1.1):
    global talk_history_
    with get_lock("talk_history"):
        talk_history_.append({"role": "system", "content": f"{speaker_name}: {text}"})
        if len(talk_history_) > 5:
            talk_history_ = talk_history_[-5:]

    with get_lock("tts_queue"):
        tts_queue_.append((text, speed))


request_stop_speak = False


#
# 音声再生
#
@fire_and_forget
def run_speak_thread():
    global request_stop_speak, play_obj_
    global app_done_
    while not app_done_:
        try:
            if play_obj_ is not None and play_obj_.is_playing():
                if request_stop_speak:
                    play_obj_.stop()
                    play_obj_ = None
                    request_stop_speak = False
                else:
                    time.sleep(0.05)
                continue

            text, wav = "", None
            with get_lock("speak_queue"):
                if len(speak_queue_) > 0:
                    text, wav, _ = speak_queue_.pop(0)

            if len(text) > 0:
                print(f"[run_speak_thread] Start: {text}", flush=True)
                since = time.time()
                speak(text, wav)
                print(
                    f"[run_speak_thread] Finish: {text} | elapsed {time.time() - since:.2f} sec",
                    flush=True,
                )

            time.sleep(0.05)

        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            app_done_ = True
            break


play_obj_ = None


def speak(text, wav):
    global play_obj_

    # OBSの字幕変更
    OBS.set_text("zundamon_zimaku", text)

    # 音声再生
    play_obj_ = simpleaudio.play_buffer(wav, 1, 2, 24000)


def request_speak(text, wav, category="normal"):
    with get_lock("speak_queue"):
        if category == "normal":
            speak_queue_.append((text, wav, category))
        elif category == "mk8dx":
            # mk8dxの実況コメントは最新のものだけなる早で再生したい
            for i in range(len(speak_queue_) - 1, -1, -1):
                if speak_queue_[i][2] == "mk8dx":
                    del speak_queue_[i]
            speak_queue_.append((text, wav, category))
        elif category == "mk8dx_reaction":
            speak_queue_.insert(0, (text, wav, category))
        print("[request_speak] # of speak_queue_", len(speak_queue_))


def cancel_speak():
    with get_lock("speak_queue"):
        speak_queue_.clear()


#
# マリカの画面を解析して実況させる
#


mk8dx_game_state_ = ""


from typing import NamedTuple, Tuple


class MK8DXStatus(NamedTuple):
    n_coin: int = 0
    n_lap: int = 1
    item_omote: str = "none"
    item_ura: str = "none"
    place: str = "--"
    lap_time: float = 0


def parse_mk8dx_screen(img, cur_status: MK8DXStatus) -> Tuple[str, MK8DXStatus]:
    global mk8dx_raw_history_

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
        place = [0, "--"]

    # OCR系は変な数値だったら無効
    if not (0 <= n_coin <= 10):
        ret_coin = False
    if not (0 <= n_lap <= 3):
        ret_lap = False

    # コイン・ラップが見えていたらレース中なはず
    is_racing = ret_coin and ret_lap  # and place[1] != "-1"

    # ゲーム状態
    game_state = ""
    if not is_racing:
        return game_state, cur_status

    if is_finished:
        game_state = "FINISH"
    else:
        game_state = "RACING"

    # 生のパース結果を保存する。直近3F分だけ保持
    raw_status = MK8DXStatus(n_coin, n_lap, omote[1], ura[1], place[1])
    mk8dx_raw_history_.append(raw_status)
    if len(mk8dx_raw_history_) < 3:
        return game_state, cur_status
    else:
        mk8dx_raw_history_ = mk8dx_raw_history_[-3:]

    # 直近のパース結果をもとに、各要素を決定していく
    # rawsが全部同じだったら採用。さもなくばoldを返す
    def _update(raws, old):
        for i in range(1, len(raws)):
            if raws[0] != raws[i]:
                return old
        return raws[0]

    new_status = MK8DXStatus(
        _update([r.n_coin for r in mk8dx_raw_history_], cur_status.n_coin),
        _update([r.n_lap for r in mk8dx_raw_history_], cur_status.n_lap),
        _update([r.item_omote for r in mk8dx_raw_history_], cur_status.item_omote),
        _update([r.item_ura for r in mk8dx_raw_history_], cur_status.item_ura),
        _update([r.place for r in mk8dx_raw_history_], cur_status.place),
    )

    return game_state, new_status


def update_game_state(game_state, cur_status, prev_n_coin, finish_time):
    global mk8dx_spoken_result_

    prev_state = mk8dx_game_state_

    if game_state == "FINISH":
        # FINISHは即時反映
        mk8dx_game_state_ = game_state
        finish_time = time.time()
    elif time.time() - finish_time > 15:
        # FINISHになって15秒経過したら更新許可
        mk8dx_game_state_ = game_state

    is_state_changed = prev_state != mk8dx_game_state_
    if is_state_changed and mk8dx_game_state_ == "FINISH":
        # レース中のセリフをキャンセル（即停止まではしない）
        cancel_speak()
        # 順位について話すことを許可
        mk8dx_spoken_result_ = False

    if is_state_changed and mk8dx_game_state_ == "":
        # レース状態でなくなったらもろもろリセット
        reset_mk8dx()
        cur_status = MK8DXStatus()
        prev_n_coin = 0

    if is_state_changed:
        # OBSにゲーム画面のステートを伝える
        send_mk8dx_game_state_to_OBS(mk8dx_game_state_)

    return cur_status, prev_n_coin, finish_time


def mk8dx_reaction():
    global request_stop_speak
    answer, category = think_mk8dx_reaction()
    wav = tts(answer, 1.5)
    request_stop_speak = True
    request_speak(answer, wav, category)
    print("[request_reaction]", answer, category)


def update_race_status(cur_status, prev_lap, lap_start_time):
    global mk8dx_status_updated_

    # 被弾判定
    if prev_n_coin > cur_status.n_coin:
        mk8dx_reaction()
    prev_n_coin = cur_status.n_coin

    # ラップが変わった
    if prev_lap != cur_status.n_lap:
        prev_lap = cur_status.n_lap
        lap_start_time = time.time()
    cur_status.lap_time = time.time() - lap_start_time

    # OBSにステータスを伝える
    send_mk8dx_status_to_OBS(cur_status)

    # ステータスを履歴に保存
    with get_lock("mk8dx_status"):
        mk8dx_status_history_.append(cur_status)
        if len(mk8dx_status_history_) > 2:
            # とりあえず今と直前の2要素だけあればよい
            mk8dx_status_history_ = mk8dx_status_history_[-2:]
        mk8dx_status_updated_ = True

    return cur_status, prev_lap, lap_start_time


@fire_and_forget
def run_mk8dx_game_capture_thread():
    global mk8dx_spoken_result_, mk8dx_game_state_
    global app_done_, mk8dx_status_history_, mk8dx_status_updated_

    print("[run_mk8dx_game_capture_thread] Start")
    lap_start_time = time.time()
    finish_time = 0
    prev_lap = -1
    prev_n_coin = 0

    cur_status = MK8DXStatus()
    while not app_done_:
        try:
            since = time.time()

            # ゲーム画面を解析
            img = OBS.capture_game_screen()
            game_state, cur_status = parse_mk8dx_screen(img, cur_status)

            # ゲームステートの更新
            cur_status, prev_n_coin, finish_time = update_game_state(
                game_state, cur_status, prev_n_coin, finish_time
            )

            if mk8dx_game_state_ != "RACING":
                time.sleep(0.1)
                continue

            # レース詳細の更新
            cur_status, prev_lap, lap_start_time = update_race_status(
                cur_status, prev_lap, lap_start_time
            )

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
        prev_status = None
        while not app_done_:
            try:
                since = time.time()

                cur_status = None
                with get_lock("mk8dx_status"):
                    if mk8dx_status_updated_:
                        if len(mk8dx_status_history_) >= 1:
                            cur_status = mk8dx_status_history_[-1]
                        mk8dx_status_updated_ = False

                # フィニッシュ画面は黙る
                if mk8dx_game_state_ == "RACING":
                    time.sleep(0.1)
                    continue

                # 更新ないのでスキップ
                if cur_status is None:
                    time.sleep(0.1)
                    continue

                latest_place_ = cur_status.place
                answer, category = think_mk8dx(cur_status)

                if len(answer) >= 1:
                    # 喋った内容を保存
                    f.write(
                        f"{cur_status.place},{cur_status.item_omote},{cur_status.item_ura},{cur_status.n_lap},{cur_status.n_coin},{answer}\n"
                    )
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
                    if mk8dx_game_state_ != "RACING":
                        request_speak(answer, wav, category)

                print(
                    f"[run_mk8dx] {answer} ({category}) | elapsed {time.time() - since:.2f} sec",
                    flush=True,
                )
                time.sleep(0.1)
            except Exception as e:
                print(str(e), "\n", traceback.format_exc(), flush=True)
                app_done_ = True
                break


def send_mk8dx_status_to_OBS(n_coin, n_lap, lap_time, omote, ura, place):
    text = f"順位: {place[1]}\n"
    text += f"アイテム: {omote[1]}, {ura[1]}\n"
    text += f"コイン: {n_coin}枚\n"
    text += f"ラップ: {n_lap}週目 ({lap_time:.1f}秒)\n"
    OBS.set_text("mk8dx_status", text)


def send_mk8dx_game_state_to_OBS(game_state):
    OBS.set_text("mk8dx_status_finish", game_state)


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

            # 特定ワードで決め打ちの処理を行う
            talked_any = play_scenario(author, question, is_mk8dx_mode_)
            if talked_any:
                prev_listen_time = time.time()
                time.sleep(0.1)
                continue

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

            # 質問文を読み上げる
            request_tts("User", "「" + question + "」", speed=1.3)

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
    global youtube_chat_, is_mk8dx_mode_

    # youtube
    youtube_chat_ = pytchat.create(video_id=args.chat_video_id)

    # openai
    OpenAILLM.init(Path("data/config/mk8dx/prompt.json"))

    # obs
    OBS.init(args.obs_pass)
    OBS.set_browser_url(
        "ブラウザ 2",
        f"https://www.youtube.com/live_chat?is_popout=1&v={args.chat_video_id}",
    )

    # mk8dx
    is_mk8dx_mode_ = args.mk8dx
    if is_mk8dx_mode_:
        MK8DX.init(Path("data/mk8dx_images"))
        reset_mk8dx(True)

    # monologue
    global all_monologues_
    with open("data/soliloquys.txt", encoding="utf8") as f:
        all_monologues_ = [line.strip() for line in f if len(line.strip()) > 1]

    with open("data/config/mk8dx/damage_voice.txt", "r", encoding="utf-8") as f:
        for text in f:
            text = text.strip()
            damage_voices.append(text)
            tts_cache_[text] = tts(text, 1.5)


damage_voices = []
tts_cache_ = {}


def reset_mk8dx(reset_zimaku=False):
    global mk8dx_status_history_, mk8dx_status_updated_, mk8dx_game_state_
    with get_lock("mk8dx_history"):
        mk8dx_status_history_ = []
        mk8dx_status_updated_ = False
        mk8dx_game_state_ = ""
    if reset_zimaku:
        OBS.set_text("zundamon_zimaku", "")
        send_mk8dx_status_to_OBS(0, 0, 0, [1, "--"], [1, "--"], [1, "--"])
        send_mk8dx_game_state_to_OBS(False)


async def main(args) -> None:
    # 初期化
    init(args)

    # 並行処理を起動
    run_chatbot_thread()
    run_tts_thread()
    run_speak_thread()
    if is_mk8dx_mode_:
        run_mk8dx_game_capture_thread()
        run_mk8dx_think_tts_thread()

    # メインループは何もしない（ヘルスチェックくらいする？)
    while True:
        if app_done_:
            break
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
