import time
from typing import Dict, List, Tuple
import openai
import os
import re
import json
import traceback
from pathlib import Path

prompt_path_ = None
prompt_data_ = {}
prev_mk8dx_status_ = ""
format_cache_ = {}


def load_format(msg):
    rel_path = msg["role"].split("@")[1].strip()
    path = prompt_path_.parent / rel_path
    if str(path) not in format_cache_:
        with open(path, "r", encoding="utf-8") as f:
            format_cache_[str(path)] = f.read().strip()
    return format_cache_[str(path)]


def make_prompt(question, chat_history):
    prompt = []

    for msg in prompt_data_["default"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "question@":
            prompt.append({"role": "user", "content": question})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        else:
            prompt.append(msg)

    return prompt


def chat_completion(prompt: List, timeout: float) -> Tuple[bool, str]:
#    return True, "ああ、ずんだ餅がやばいのだ"
    for _ in range(3):
        try:
            print(f"[chat_completion] start", flush=True)
            since = time.time()
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                request_timeout=timeout,
            )
            content = response["choices"][0]["message"]["content"]
            # print(
            #     f"[chat_completion] content={content} | Elapsed {time.time() - since:.2f} sec",
            #     flush=True,
            # )
            return True, content
        except openai.error.RateLimitError as e:
            print("Prompt:", prompt, flush=True)
            print(str(e), "\n", traceback.format_exc(), flush=True)
            time.sleep(1)
        except openai.error.APIError as e:
            print("Prompt:", prompt, flush=True)
            print(str(e), "\n", traceback.format_exc(), flush=True)
            time.sleep(1)
        except Exception as e:
            print("Prompt:", prompt, flush=True)
            print(str(e), "\n", traceback.format_exc(), flush=True)
            time.sleep(1)
    return False, ""


def chat_completion_postprocess(content: str) -> str:
    def remove_after(content, chars):
        for ch in chars:
            pos = content.find(ch)
            if pos >= 0:
                content = content[:pos]
        return content

    # remove whitespace
    content = re.sub(r"\s+", "", content)

    # ずんだもん：XXXX の形式でかえってきたときの対応
    if content.startswith("ずんだもん:"):
        content = content[len("ずんだもん:") :]
    if content.startswith("ずんだもん："):
        content = content[len("ずんだもん：") :]

    # 文の先頭・末尾から余計な文字を消す
    ignore_chars = '<@.+>「」()#。"' + "'"
    content = content.strip(ignore_chars)

    # 文中の#をけす
    content = remove_after(content, "#＃")

    # "(XX文字)" を消す
    for ch in "(（":
        pos = content.find(ch)
        if pos >= 0:
            after = content[pos:]
            if "文字" in after:
                content = content[:pos]

    # 「」
    # content = remove_after(content, "()#（）「」")

    # 語尾ミスったのを補正
    content = content.replace("ののだ", "なのだ")
    content = content.replace("のだか？", "のだ？")

    # あたらめて余計な文字消す
    content = content.strip(ignore_chars)

    return content


def ask(text: str, chat_history: List, timeout: float = 12) -> Tuple[bool, str]:
    text = re.sub("<@.+>", "", text)
    prompt = make_prompt(text, chat_history)
    ret, content = chat_completion(prompt, timeout)
    if not ret:
        return ret, ""
    answer = chat_completion_postprocess(content)
    return ret, answer


#
# MK8dx
#


def make_prompt_mk8dx_race(
    n_coin: int,
    n_lap: int,
    lap_time: float,
    omote: str,
    ura: str,
    place: str,
    delta_coin: int,
    chat_history: List,
):
    global prev_mk8dx_status_

    prompt = []

    for msg in prompt_data_["mk8dx_race"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        elif msg["role"] == "previous_status@":
            prompt.append({"role": "user", "content": prev_mk8dx_status_})
        elif msg["role"].startswith("status@"):
            lap_position = "前半" if lap_time > 20 else "後半"
            additional_info = "・あなたはたった今、被弾してコインを失いました" if delta_coin < 0 else ""
            status = load_format(msg).format(
                place, omote, ura, n_coin, n_lap, lap_position, additional_info
            )
            prompt.append({"role": "user", "content": status})
            prev_mk8dx_status_ = status
        else:
            prompt.append(msg)

    return prompt


def make_prompt_mk8dx_result(place, chat_history):
    prompt = []

    for msg in prompt_data_["mk8dx_result"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        elif msg["role"].startswith("result@"):
            prompt.append({"role": "user", "content": load_format(msg).format(place)})
        elif msg["role"].startswith("impression@"):
            prompt.append({"role": "user", "content": load_format(msg).format(place)})
        else:
            prompt.append(msg)

    return prompt


def ask_mk8dx(
    n_coin,
    n_lap,
    lap_time,
    omote,
    ura,
    place,
    delta_coin,
    chat_history,
    is_race_mode,
    timeout=8,
):
    global prev_mk8dx_status_
    if is_race_mode:
        prompt = make_prompt_mk8dx_race(
            n_coin, n_lap, lap_time, omote, ura, place, delta_coin, chat_history
        )
    else:
        prompt = make_prompt_mk8dx_result(place, chat_history)

    ret, content = chat_completion(prompt, timeout)
    if not ret:
        return ret, ""

    answer = chat_completion_postprocess(content)
    return ret, answer


def reset_mk8dx():
    global prev_mk8dx_status_
    prev_mk8dx_status_ = ""


#
# Initialize
#
def init(prompt_path: Path):
    global prompt_data_, prompt_path_

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    # load json file
    with open(prompt_path, "r", encoding="utf8") as f:
        prompt_data_ = json.load(f)
    prompt_path_ = prompt_path


if __name__ == "__main__":

    def main() -> None:
        init(Path("../data/config/mk8dx/prompt.json"))

        while True:
            prompt = input("Input:")
            ret, answer = ask(prompt, [])
            print("Answer(ask              ):", ret, answer)

            # ret, answer = ask_mk8dx(5, 3, "キラー", "スター", "10", [], True)
            # print("Answer(ask_mk8dx, race  ):", ret, answer)

            # ret, answer = ask_mk8dx(0, 0, "", "", "1", [], False)
            # print("Answer(ask_mk8dx, result):", ret, answer)

    main()
