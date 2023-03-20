from argparse import ArgumentParser


def init():
    # TODO: いろいろ初期化
    pass


def listen():
    # TODO: youtubeのチャット欄を読む
    prompt = input("Enter prompt: ")
    return prompt


def think(prompt):
    # TODO: OBSで質問文表示
    # TODO: OpenAI APIで回答生成
    if prompt == "初見です":
        return "初見は帰るのだ"
    answer = prompt
    return answer


def speak(text):
    # TODO: OBSの字幕変更
    # TODO: VOICEVOXで回答を喋らせる
    print(text)


def main(args) -> None:
    init()
    while True:
        prompt = listen()
        if prompt == "exit":
            break
        answer = think(prompt)
        speak(answer)


def parse_args():
    argparser = ArgumentParser()
    args = argparser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())
