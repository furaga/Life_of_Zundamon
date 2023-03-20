import dataclasses
import json
import logging
from argparse import ArgumentParser
from pathlib import Path
from typing import Tuple


def main(args) -> None:
    while True:
        prompt = input("Enter prompt: ")
        if prompt == "exit":
            break
        if prompt == "初見です":
            print("初見は帰るのだ")
        else:
            print(prompt)


def parse_args():
    argparser = ArgumentParser()
    args = argparser.parse_args()
    return args


if __name__ == "__main__":
    main(parse_args())