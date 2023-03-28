import time
from typing import Dict, List, Tuple
import openai
import os
import re
import json
from pathlib import Path

prompt_path_ = Path(".")
prompt_dict_ = {}
prev_mk8dx_status_ = ""
format_cache_ = {}


def load_format(msg):
    rel_path = msg["role"].split("@")[1].strip()
    path = prompt_path_ / rel_path
    if str(path) not in format_cache_:
        with open(path, "r", encoding="utf-8") as f:
            format_cache_[str(path)] = f.read().strip()
    return format_cache_[str(path)]


def make_prompt(question, chat_history):
    prompt = []

    for msg in prompt_dict_["default"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "question@":
            prompt.append({"role": "user", "content": question})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        else:
            prompt.append(msg)

    return prompt


def chat_completion(prompt: List, timeout: float) -> Tuple(bool, Dict):
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


def ask(text: str, chat_history: List, timeout: float = 8) -> Tuple(bool, str):
    text = re.sub("<@.+>", "", text)
    prompt = make_prompt(text, chat_history)
    ret, content = chat_completion(prompt, timeout)
    if not ret:
        return ret, ""
    answer = chat_completion_postprocess(content)
    return ret, answer


def make_prompt_mk8dx_race(n_coin, n_lap, omote, ura, place, chat_history):
    global prev_mk8dx_status_

    prompt = []

    for msg in prompt_dict_["mk8dx_race"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        elif msg["role"] == "previous_status@":
            prompt.append({"role": "user", "content": prev_mk8dx_status_})
        elif msg["role"].startswith("status@"):
            status = load_format(msg).format(n_coin, n_lap, omote, ura, place)
            prompt.append({"role": "user", "content": status})
            prev_mk8dx_status_ = status
        else:
            prompt.append(msg)

    return prompt


def make_prompt_mk8dx_result(place, chat_history):
    prompt = []

    for msg in prompt_dict_["mk8dx_race"]:
        if msg["role"].startswith("personality@"):
            prompt.append({"role": "user", "content": load_format(msg)})
        elif msg["role"] == "chat_history@":
            prompt += chat_history
        elif msg["role"] == "result@":
            prompt.append({"role": "user", "content": load_format(msg).format(place)})
        elif msg["role"] == "impression@":
            prompt.append({"role": "user", "content": load_format(msg).format(place)})
        else:
            prompt.append(msg)

    return prompt


def ask_mk8dx(
    n_coin, n_lap, omote, ura, place, chat_history, race_mode=True, timeout=8
):
    global prev_mk8dx_status_
    if race_mode:
        prompt = make_prompt_mk8dx_race(n_coin, n_lap, omote, ura, place, chat_history)
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


def init_openai(prompt_path):
    global prompt_dict_, prompt_path_

    openai.api_key = os.environ.get("OPENAI_API_KEY")

    # load json file
    with open(prompt_path, "r") as f:
        prompt_path_ = prompt_path
        prompt_dict_ = json.load(f)


if __name__ == "__main__":

    def main() -> None:
        init_openai()

        while True:
            prompt = input("Input:")
            _, answer = ask(prompt, [])
            print("Answer:", answer)

    main()
