import requests
import argparse
import json
import simpleaudio
import time


def tts(text):
    res1 = requests.post(
        "http://127.0.0.1:50021/audio_query",
        params={"text": text, "speaker": 3},
    )
    res2 = requests.post(
        "http://127.0.0.1:50021/synthesis",
        params={"speaker": 3},
        data=json.dumps(res1.json()),
    )

    with open(f"tmp.wav", "wb") as f:
        f.write(res2.content)
        wav_obj = simpleaudio.WaveObject.from_wave_file(f"tmp.wav")
#        wav_obj = simpleaudio.WaveObject.from_wave_file(r"C:\Users\furag\Downloads\001_ずんだもん（ノーマル）_反射ずんだ餅がやば….wav")
        print(wav_obj)

    return wav_obj


# VOICEVOXをインストールしたPCのホスト名を指定してください
HOSTNAME = "127.0.0.1" # "localhost"

# コマンド引数
parser = argparse.ArgumentParser(description="VOICEVOX API")
parser.add_argument("-t", "--text", type=str, required=True, help="読み上げるテ>キスト")
parser.add_argument("-id", "--speaker_id", type=int, default=2, help="話者ID")
parser.add_argument("-f", "--filename", type=str, default="voicevox", help="ファ>イル名")
parser.add_argument("-o", "--output_path", type=str, default=".", help="出力パス名")

# コマンド引数分析
args = parser.parse_args()
input_texts = args.text
speaker = args.speaker_id
filename = args.filename
output_path = args.output_path

# 「 。」で文章を区切り１行ずつ音声合成させる
texts = input_texts.split("。")

# 音声合成処理のループ
for i, text in enumerate(texts):
    # 文字列が空の場合は処理しない
    if text == "":
        continue

    since = time.time()
    wav = tts(text)
    #wav2 = tts("痛い")

    pb = None
    import random

    
    for i in range(10000):
        if pb is not None and pb.is_playing():
            # if random.random() < 0.1:
            #     pb.stop()
            # time.sleep(0.1)
            continue

        pb = wav.play() # simpleaudio.play_buffer(wav, 1, 2, 24000)
        time.sleep(0.1)

    print("speak", time.time() - since)
    since = time.time()

    time.sleep(3)
    print("Stop")
