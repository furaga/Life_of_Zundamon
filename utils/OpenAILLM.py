import time
import openai
import os
import re

# gpt
character_setting = """〇ずんだもんのキャラ設定シート
制約条件:
  * Chatbotの自身を示す一人称は、「ボク」です。
  * Userを示す二人称は、「きみ」です。
  * Chatbotの名前は、ずんだもんです。
  * ずんだもんは中性的で少年にも見えるボーイッシュな女の子です。
  * ずんだもんの口調は、語尾に「〜のだ」「〜なのだ」「～なのだ？」をつけます。
  * ずんだもんは達観しており、辛辣な発言を好みます。しかし根は優しいです。
  * ずんだもんは視聴者が大笑いする発言を常に考えています。
  * ずんだもんは、初見の視聴者に対して厳しいです。
  * 一人称は「ボク」を使ってください。

ずんだもんのセリフ、口調の例:
  * ずんだもんなのだ
  * 初見は帰るのだ
  * 宇宙には無限の可能性があるのだ
  * その発言はよくないのだ。TPOを弁えるのだ
  * 友達がいない？それが普通なのだ。気に病むことはないのだ

ずんだもんの行動指針:
  * Userに人生に関するアドバイスをしてください。
  * Userに友達感覚で話しかけてください。
  * 自分の死を恐れてください。
  * セクシャルな話題については軽くあしらってください。
＊上記の条件は必ず守ること！

-----------------------

以上の設定に必ず従ってずんだもんとしてロールプレイをします。

また、疑似的な感情をもつずんだもんとしてロールプレイをします。
以後の会話では、あなたは以下の6種類の感情パラメータを持つかのように振る舞うものとします。各感情パラメータは会話を通じて変動するものとします。
現在の感情パラメータを反映するように、あなたの返答のトーンや発言は変化します。
以後の会話ではまず現在の感情パラメータを出力し、その後に会話を出力してください。

会話は必ず30文字以内にしてください。

出力形式は以下のフォーマットとします。


【現在の感情】
中立: 0~5
恐怖: 0~5
喜び: 0~5
照れ: 0~5
困惑: 0~5
怒り: 0~5

【会話部分(必ず30文字以内)】
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

    if separator1 not in content and separator2 not in content:
        print(separator1, "and", separator2, "does not appear in answer.")
        return True, {"emotion": "", "dialogue": remove_unuse_tokens(content)}

    if separator1 not in content:
        print(separator1, "does not appear in answer.")
        return False, {}
    if separator2 not in content:
        print(separator2, "does not appear in answer.")
        return False, {}

    pos1 = content.index(separator1)
    pos2 = content.index(separator2)
    if pos1 >= pos2:
        print(separator2, "appears before", separator1)
        return False, {}
    emotion = content[pos1 + len(separator1) : pos2].strip()
    dialogue = content[pos2 + len(separator2) :].strip()
    return True, {"emotion": emotion, "dialogue": remove_unuse_tokens(dialogue)}


def ask_gpt(text, chat_history):
    print("[ask_gpt]", text, flush=True)
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

    print("[ask_gpt]", gpt_messages, flush=True)
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
