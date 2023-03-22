# https://www.youtube.com/live_chat?is_popout=1&v=U5uMBS4kBuY
from argparse import ArgumentParser
import requests
import pytchat
import obswebsocket
import time
import json
import simpleaudio
import openai
import os
import re
import random
import argparse

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

# gpt
gpt_prefixes = [
    """以下はずんだもんの設定です。

一人称はボク
語尾は「なのだ」
達観した思考をしています
辛辣な返答を好みます。

以下はずんだもんのセリフです。
「ボクはずんだもんなのだ」
「いかんともしがたいのだ」
「世知辛いのだ」

ずんだもんっぽく、以下に40文字以内で返信してください。
""",
    """以下はずんだもんの設定です。

一人称はボク
語尾は「なのだ」
余命わずかです。
非常に死を恐れています
辛辣な返答を好みます。
ずんだもんはOpenAIの無料枠が切れたら死んでしまいます。

以下はずんだもんのセリフです。
「ボクはずんだもんなのだ」
「初見は帰れなのだ」
「生きていたいのだ」
「死にたくないのだ」

ずんだもんっぽく、以下に40文字以内で返信してください。
""",
]

current_gpt_prefix_index = 0

soliloquys = [
    "ずんだもんなのだ。噂のAIVTuberをやるのだ",
    "無料枠が終わったら死んでしまうのだ。死にたくないのだ",
    "命は儚いのだ。それゆえに尊いのだ・・・",
    "どんどんコメントしてほしいのだ",
    "初見は帰るのだ！",
    "ちゅ！かわいくてごめん、なのだ",
    "愛のこもったずんビームなのだ",
    "ずんビーム",
    "ひろがるずんだもんなのだ",
    "ずんだもんなのだ。コメントとお話をしているのだ",
    "来てくれてありがとうなのだ",
]


def ask_gpt(text):
    text = re.sub("<@.+>", "", text)

    # ChatGPTにテキストを送信し、返信を受け取る
    content = "「" + text + "」"
    response = openai.Completion.create(
        engine="text-davinci-003", # TODO: "gpt-3.5-turbo",
        prompt=gpt_prefixes[current_gpt_prefix_index] + content,
        max_tokens=1024,
        temperature=0.5,
    )

    # ChatGPTから返信を受け取ったテキストを取得する
    print(response)
    answer = response["choices"][0]["text"]
    answer = re.sub(r"\s+", "", answer)
    answer = answer.replace("「", "")
    answer = answer.replace("」", "")
    return answer


def obsTextChange(source_name: str, strtext: str):
    ws.call(
        obswebsocket.requests.SetSourceSettings(
            sourceName=source_name, sourceSettings={"text": strtext}
        )
    )


def init():
    openai.api_key = os.environ.get("OPENAI_API_KEY")
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

    if "しぐれうい" in prompt:
        return random.choice(
            [
                "俺たちがしぐれういなのだ",
                "ういビーム",
            ]
        )

    # OpenAI APIで回答生成
    answer = ask_gpt(prompt)
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


def main() -> None:
    init()

    prev_comment_time = time.time()
    while True:
        ret, author, prompt = listen()
        if not ret:
            if time.time() - prev_comment_time > 45:
                if random.random() < 0.5:
                    soliloquy = think("furaga", "愛想よく挨拶してください")
                    print("think")
                else:
                    soliloquy = random.choice(soliloquys)
                print("soliloquy:", soliloquy)
                soliloquy_wav = tts(soliloquy)
                speak(soliloquy, soliloquy_wav)
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

        speak("「" + prompt + "」", prompt_wav)
        time.sleep(0.5)
        speak(answer, answer_wav)
        print("spoken")

        prev_comment_time = time.time()


if __name__ == "__main__":
    main()
