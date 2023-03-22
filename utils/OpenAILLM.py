import time
import openai
import os
import re

# gpt
character_setting = """〇ずんだもんのキャラ設定シート
制約条件:
  * ずんだもんの一人称は、「ボク」です。
  * Userを示す二人称は、「きみ」です。
  * ずんだもんは中性的で少年にも見えるボーイッシュな女の子です。
  * ずんだもんの口調は、語尾に「〜のだ」「〜なのだ」「～なのだ？」をつけます。
  * ずんだもんは達観しており、辛辣な発言を好みます。しかし根は優しいです。
  * 一人称は「ボク」を使ってください。

ずんだもんのセリフ、口調の例:
  * ずんだもんなのだ
  * 友達がいない？それが普通なのだ。気に病むことはないのだ

ずんだもんの行動指針:
  * Userに人生に関するアドバイスをしてください。
  * Userに友達感覚で話しかけてください。
  * セクシャルな話題については軽くあしらってください。
＊上記の条件は必ず守ること！

-----------------------

出力形式は以下のフォーマットです。必ず40文字以内の文章を出力してください。

了解したのだ。それでははじめるのだ。
"""

gpt_messages_format = [
    {"role": "system", "content": character_setting},
    {"role": "system", "content": "下記はここまでの会話です。"},
    {"role": "chat_history"},
    {"role": "system", "content": "下記は直前の会話です。"},
    {"role": "prompt"},
]


def parse_content(content):
    print("/////////////")
    print(content)
    print("/////////////")

    def remove_unuse_tokens(text):
        if text.startswith("ずんだもん:"):
            text = text[len("ずんだもん:") :]
        return text.strip()

    separator1 = "【現在の感情】"
    separator2 = "【会話部分(必ず30文字以内)】"

    if separator1 not in content or separator2 not in content:
        print(separator1, "and", separator2, "does not appear in answer.")
        return True, {"emotion": "", "dialogue": remove_unuse_tokens(content)}

    pos1 = content.index(separator1)
    pos2 = content.index(separator2)
    if pos1 >= pos2:
        print(separator2, "appears before", separator1)
        return False, {}
    emotion = content[pos1 + len(separator1) : pos2].strip()
    dialogue = content[pos2 + len(separator2) :].strip()
    return True, {"emotion": emotion, "dialogue": remove_unuse_tokens(dialogue)}


def ask_gpt(text, chat_history):
    # print("[ask_gpt]", text, flush=True)
    text = re.sub("<@.+>", "", text)

    # ChatGPTにテキストを送信し、返信を受け取る
    gpt_messages = []
    for msg in gpt_messages_format:
        if msg["role"] == "chat_history":
            gpt_messages += chat_history
        elif msg["role"] == "prompt":
            gpt_messages.append({"role": "user", "content": text})
        else:
            gpt_messages.append(msg)

    #  print("[ask_gpt]", gpt_messages, flush=True)
    for _ in range(3):
        try:
            since = time.time()
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=gpt_messages,
            )
            content = response["choices"][0]["message"]["content"]
            print(f"[ask_gpt] ChatCompletion | elapsed {time.time() - since:.2f} sec")
            ret, answer = parse_content(content)
            print(f"[ask_gpt] parse_content | elapsed {time.time() - since:.2f} sec")
            if not ret:
                print("[ask_gpt] Failed to parse content from openai")
                continue
            return ret, answer
        except openai.error.RateLimitError:
            print("[ask_gpt] rate limit error")
            time.sleep(1)
        except openai.error.APIError:
            print("[ask_gpt] API error")
            time.sleep(1)

    return False, {}


def init_openai():
    openai.api_key = os.environ.get("OPENAI_API_KEY")


if __name__ == "__main__":

    def main() -> None:
        init_openai()

        while True:
            prompt = input("Input:")
            _, answer = ask_gpt(prompt, [])
            print("Answer:", answer)

    main()
