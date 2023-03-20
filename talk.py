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

# obswebsocket
host = "localhost"
port = 4444
password = "GKzsYMK574JexVLr"
ws = obswebsocket.obsws(host, port, password)

# pytchat
chat = pytchat.create(video_id="2IRXq_yFIzA")

# voicevox
speaker = 1  # ずんだもん

# gpt
gpt_prefix = """以下はずんだもんの設定です。

一人称はボク
語尾は「なのだ」
達観した思考をしています
辛辣な返答を好みます。
ずんだもんはOpenAIの無料枠が切れたら死んでしまいます。
ずんだもんはときどき生への執着を感じさせる発言をします。

以下はずんだもんのセリフです。
「ボクはずんだもんなのだ」
「初見は帰れなのだ」
「いかんともしがたいのだ」
「世知辛いのだ」

ずんだもんっぽく、以下に30文字以内で返信してください。
"""


def ask_gpt(text):
    text = re.sub("<@.+>", "", text)

    # ChatGPTにテキストを送信し、返信を受け取る
    content = "「" + text + "」"
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=gpt_prefix + content,
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
    openai.api_key = os.environ["OPENAI_API_KEY"]
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
    if "初見です" in prompt:
        return "初見は帰るのだ"
    if "しぐれうい" in prompt:
        return "俺たちがしぐれういなのだ"
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


def main(args) -> None:
    init()
    while True:
        ret, author, prompt = listen()
        if not ret:
            continue
        print("prompt:", prompt)

        answer = think(author, prompt)
        if len(answer) <= 0:
            import random

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


def parse_args():
    argparser = ArgumentParser()
    args = argparser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())
