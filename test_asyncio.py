import asyncio
import traceback
import threading
import time

from utils.asyncio_util import fire_and_forget

is_finish = False
value = 0

threadlock = threading.RLock()

@fire_and_forget
def run_loop(name):
    global is_finish, value
    cnt = 0
    while not is_finish:
        try:
            print(f"[{name}] thread {threading.get_ident()}, cnt {cnt}", flush=True)
            with threadlock:
                value = value + 1
            time.sleep(1)
            pass
        except Exception as e:
            print(str(e), "\n", traceback.format_exc(), flush=True)
            is_finish = True
            break


def main():
    global is_finish

    run_loop("A")
    run_loop("B")
    run_loop("C")

    # メインループは何もしない（ヘルスチェックくらいする？)
    try:
        while True:
            print("value =", value, flush=True)
            time.sleep(1)
    except:
        pass
    finally:
        is_finish = True


if __name__ == "__main__":
    main()
