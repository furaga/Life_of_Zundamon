import time
from typing import Dict, List, Tuple
import openai
import os
import re
import json
from pathlib import Path

prompt_data_cache_ = {}
prompt_path_ = Path(".")


def make_prompt(key, question, chat_history):
    prompt = []

    for msg in prompt_dict_[key]:
        if msg["role"].startswith("personality@"):
            rel_path = msg["role"].split("@")[1].strip()
            personality_path = prompt_path_ / rel_path

            if "personality" not in prompt_data_cache_:
                with open(personality_path, "r", encoding="utf-8") as f:
                    prompt_data_cache_["personality"] = f.read().strip()
            personality = prompt_data_cache_["personality"]
            prompt.append(
                {
                    "role": "user",
                    "content": personality,
                }
            )
        elif msg["role"] == "question@":
            prompt.append({"role": "user", "content": question})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        else:
            prompt.append(msg)

    return prompt


def chat_completion(prompt: List, timeout: float) -> (bool, Dict):
    for _ in range(3):
        try:
            since = time.time()
            print(f"[ask_gpt] ChatCompletion start", flush=True)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                timeout=10,
            )
            content = response["choices"][0]["message"]["content"]
            print(f"[ask_gpt] ChatCompletion finish", flush=True)
            return True, content
        except openai.error.RateLimitError:
            print("[ask_gpt] rate limit error")
            time.sleep(1)
        except openai.error.APIError:
            print("[ask_gpt] API error")
            time.sleep(1)
        except:
            print("[ask_gpt] API error")
            time.sleep(1)
    return False, {}


def chat_completion_postprocess(content: str) -> str:
    def remove_after(content, chars):
        for ch in chars:
            pos = content.index(ch)
            if pos >= 0:
                content = content[:pos]
        return content

    # remove whitespace
    content = re.sub(r"\s+", "", content)

    # ずんだもん：XXXX の形式でかえってきたときの対応
    if content.startswith("ずんだもん:"):
        content = content[len("ずんだもん:") :]

    # 文の先頭・末尾から余計な文字を消す
    ignore_chars = '<@.+>「」()#。"' + "'"
    content.strip(ignore_chars)

    # 文中の()や#をけす
    content = remove_after(content, "()#")

    return content


def ask_gpt(text: str, chat_history: List, timeout: float = 8) -> Tuple(bool, str):
    text = re.sub("<@.+>", "", text)
    prompt = make_prompt("default", text, chat_history)
    ret, content = chat_completion(prompt, timeout)
    if not ret:
        return ret, ""
    if ret:
        answer = chat_completion_postprocess(content)
    return ret, answer


prev_status_ = ""


def ask_gpt_mk8dx(n_coin, n_lap, omote, ura, place, nf=False):
    global prev_status_

    system_prompt = """〇ずんだもんのキャラ設定シート
制約条件:
  * ずんだもんの一人称は、「ボク」です。
  * ずんだもんは中性的で少年にも見えるボーイッシュな女の子です。
  * ずんだもんの口調は、語尾に「〜のだ」「〜なのだ」「～なのだ？」をつけます。
  * ずんだもんのゆるふわ系です。「ふええ」「はわわ」といった言葉を多用します。

ずんだもんのセリフ、口調の例:
  * はわわ、ずんだもんなのだ
  * 落ち着くのだ。丁寧に走るのだ
  * ふええ、ひどいのだ

ずんだもんの行動指針:
  * マリオカート8DXのプレイ実況をしてください

＊上記の条件は必ず守ること！

あなたは上記の設定にしたがって、マリオカート8DXの実況プレイをしています。
"""

    if not nf:
        status = """・あなたの順位は{0}位です
・あなたが所持している表アイテムは {1}です
・あなたが所持している裏アイテムは {2}です
・あなたが所持しているコイン枚数は {3}枚です
・あなたは{4}周目を走っています
""".format(
            place, omote, ura, n_coin, n_lap
        )
        gpt_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "直前ののレース状況は以下の通りです"},
            {"role": "user", "content": prev_status_},
            {"role": "user", "content": "現在のレース状況は以下の通りです"},
            {"role": "user", "content": status},
            {"role": "user", "content": "この状況を踏まえて、可愛らしい実況コメントを30文字以内で出力してください。"},
        ]
        prev_status_ = status
    else:
        gpt_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"あなたはたった今、{place}位でゴールしました"},
            {
                "role": "user",
                "content": f"""以下のフォーマットで感想をを30文字以内で出力してください。

{place}位でゴールなのだ。[感想]
""",
            },
        ]

    for _ in range(3):
        try:
            since = time.time()
            print(f"[ask_gpt_mk8dx] openai.ChatCompletion.create", flush=True)
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=gpt_messages,
                timeout=10,
            )
            content = response["choices"][0]["message"]["content"]
            print(
                f"[ask_gpt_mk8dx] ChatCompletion | elapsed {time.time() - since:.2f} sec",
                flush=True,
            )
            return True, content
        except openai.error.RateLimitError:
            print("[ask_gpt_mk8dx] rate limit error")
            time.sleep(1)
        except openai.error.APIError:
            print("[ask_gpt_mk8dx] API error")
            time.sleep(1)
        except:
            print("[ask_gpt_mk8dx] API error")
            time.sleep(1)
    return False, ""


prompt_dict_ = {}


def init_openai(prompt_path):
    global prompt_dict_

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    # load json file
    with open(prompt_path, "r") as f:
        prompt_dict_ = json.load(f)


if __name__ == "__main__":

    def main() -> None:
        init_openai()

        while True:
            prompt = input("Input:")
            _, answer = ask_gpt(prompt, [])
            print("Answer:", answer)

    main()
