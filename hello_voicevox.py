import requests
import argparse
import json
import simpleaudio
import time

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
    # audio_query (音声合成用のクエリを作成するAPI)
    res1 = requests.post(
        "http://" + HOSTNAME + ":50021/audio_query",
        headers = {'Content-Type': 'application/json'},
        params={"text": text, "speaker": speaker},
    )

    print("audio_query", time.time() - since)
    since = time.time()

    # synthesis (音声合成するAPI)
    res2 = requests.post(
        "http://" + HOSTNAME + ":50021/synthesis",
        headers = {'Content-Type': 'application/json'},
        params={"speaker": speaker},
        data=json.dumps(res1.json()),
    )
    print("synthesis", time.time() - since)
    since = time.time()

    # wavファイルに書き込み
    out_path = output_path + "/" + filename + f"_{i:03d}.wav"
    with open(out_path, mode="wb") as f:
        f.write(res2.content)


    print("save", time.time() - since)
    since = time.time()

    wav = simpleaudio.WaveObject.from_wave_file(out_path)
    wav.play()
#    simpleaudio.play_buffer(res2.content, 1, 2, 24000)

    print("speak", time.time() - since)
    since = time.time()

    time.sleep(3)
    print("Stop")
