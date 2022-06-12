import os
import sys
import json
import time
import yaml
import signal
import uvicorn
import socket
import requests
import ST7789
import schedule
import numpy as np
import RPi.GPIO as GPIO
from glob import glob
from fastapi import FastAPI
from datetime import datetime
from mutagen.flac import FLAC, Picture
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Queue, Process

# 設定ファイルの読み込み
config = {}
with open("/sounds/config.yaml") as f:
    config = yaml.safe_load(f)

wakeup_time = config["alerm"]["time"]

app = FastAPI()
proc = None
queue = Queue()

disp = ST7789.ST7789(port=0, cs=1, rst=5, dc=9, backlight=13, spi_speed_hz=80 * 1000 * 1000)

BUTTONS = [5, 6, 16, 24]
LABELS = ["A", "B", "X", "Y"]
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)

default_logo_img = "/scripts/default.png"
user_logo_img = config["system"]["logo_image"]
logo_img = user_logo_img if os.path.exists(user_logo_img) else default_logo_img

current_sound = 0
sounds = []
# 入眠のための催眠音声や音楽の一覧を取得
for path in glob(os.path.join(config["hypnosis"]["sound_dir"], "*")):
    if os.path.isfile(path):
        ext = os.path.splitext(os.path.basename(path))[1]
        if ext in [".wav", ".flac"]:
            print(path)
            sounds.append(path)

# 起床時間帯は他の音楽を再生しない
def check_wakeup_time():
    if int(wakeup_time.split(":")[0]) == datetime.now().hour:
        return True
    return False


# カバー画像の展開
def extract_cover(song_file, output_file):
    try:
        var = FLAC(song_file)
        pics = var.pictures
        for p in pics:
            if p.type == 3:
                print("\nfound front cover")
                with open(output_file, "wb") as f:
                    f.write(p.data)
    except Exception as e:
        print(e)


# ボタン処理
def button_handler(pin):
    global current_sound
    label = LABELS[BUTTONS.index(pin)]
    if label == "X":
        os.system("killall aplay")
        load_img(logo_img)
        current_sound = 0
    if label == "Y":
        os.system("killall aplay")
        url = f"http://127.0.0.1:8000/sleep/hypnosis"
        requests.get(url)
    if label == "A":
        os.system("su app -c 'amixer set 'Master' 5%+'")
    if label == "B":
        os.system("su app -c 'amixer set 'Master' 5%-'")
    print("Button press detected on pin: {} label: {}".format(pin, label))


# ディスプレイに画像またはテキストを表示する
def load_img(img_file=None, text=None, color=(0, 0, 0)):
    try:
        font_ttf = "/usr/share/fonts/ipa/ipaexg.ttf"
        image = None
        clear_img()
        if img_file is not None:
            image = Image.open(img_file)
            image = image.resize((disp.width, disp.height))
        else:
            image = Image.new("RGB", (disp.width, disp.height), color)
        if text is not None:
            draw = ImageDraw.Draw(image)
            draw.font = ImageFont.truetype(font_ttf, 15)
            img_size = np.array(image.size)
            txt_size = np.array(draw.font.getsize(text))
            pos = (img_size - txt_size) / 2
            draw.text(pos, text, fill="white", stroke_width=2, stroke_fill="black")
        disp.display(image)
    except Exception as e:
        print(e)


# ディスプレイを特定の色で塗りつぶす
def clear_img(color=(255, 0, 255)):
    image = Image.new("RGB", (disp.width, disp.height), color)
    disp.display(image)


# 音楽を再生するプロセス
def player_proc(q):
    while True:
        file_name = q.get()
        while not q.empty():
            file_name = q.get()
        cover_file = "/tmp/cover.png"
        extract_cover(file_name, cover_file)
        title = os.path.splitext(os.path.basename(file_name))[0]
        if os.path.exists(cover_file):
            load_img(img_file="/tmp/cover.png", text=title)
        else:
            load_img(text=title)
        ext = os.path.splitext(os.path.basename(file_name))[1]
        print(f"play {ext} {file_name}")
        if ext == ".flac":
            os.system(f"su app -c 'flac -d -c {file_name} | aplay -f cd'")
        if ext == ".wav":
            os.system(f"su app -c 'aplay {file_name}'")
        clear_img()
        os.system("rm /tmp/cover.png")


# ボタンのイベントをハンドラに渡すプロセス
def button_proc():
    for pin in BUTTONS:
        GPIO.add_event_detect(pin, GPIO.FALLING, button_handler, bouncetime=1000)
    signal.pause()


###############################################
# API部分
###############################################

# rem睡眠時にリクエストする
@app.get("/sleep/rem")
def sleep_rem():
    try:
        if check_wakeup_time():
            return {"status": "wakeup time"}
        os.system("killall aplay")
        file_name = config["stages"]["rem"]["sound"]
        queue.put(file_name)
    except Exception as e:
        print(e)
        return {"error": str(e)}
    return {"status": "ok"}


# nonrem睡眠時にリクエストする
@app.get("/sleep/nonrem")
def sleep_nonrem():
    try:
        if check_wakeup_time():
            return {"status": "wakeup time"}
        os.system("killall aplay")
        file_name = config["stages"]["nonrem"]["sound"]
        queue.put(file_name)
    except Exception as e:
        print(e)
        return {"error": str(e)}
    return {"status": "ok"}


# 覚醒状態にリクエストする
@app.get("/sleep/wakeup")
def sleep_wakeup():
    try:
        if check_wakeup_time():
            return {"status": "wakeup time"}
        os.system("killall aplay")
        file_name = config["stages"]["wakeup"]["sound"]
        queue.put(file_name)
    except Exception as e:
        print(e)
        return {"error": str(e)}
    return {"status": "ok"}


# ボタンから呼び出される
@app.get("/sleep/hypnosis")
def sleep_hypnosis():
    global current_sound
    try:
        file_name = sounds[current_sound]
        current_sound += 1
        if current_sound >= len(sounds):
            current_sound = 0
        queue.put(file_name)
    except Exception as e:
        print(e)
        return {"error": str(e)}
    return {"status": "ok"}


# 起床時に覚醒音を流す
def play_wakeup_music():
    try:
        os.system("killall aplay")
        file_name = config["alerm"]["sound"]
        queue.put(file_name)
    except Exception as e:
        print(e)


# インターネットの接続を監視するプロセス
last_conn = True


def check_internet_connection():
    global last_conn
    host = "1.1.1.1"
    port = 53
    timeout = 3
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        if last_conn == False:
            last_conn = True
            load_img(logo_img)
    except socket.error as ex:
        if last_conn == True:
            last_conn = False
            load_img(text="Offline Internet", color=(255, 0, 0))


# 定期実行プロセスを登録
def timer_proc():
    schedule.every().day.at(wakeup_time).do(play_wakeup_music)
    schedule.every(1).minutes.do(check_internet_connection)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # 音量の初期化
    init_volume = config["system"]["init_volume_pct"]
    os.system(f"su app -c 'amixer set 'Master' {init_volume}%'")
    # 各プロセスの起動
    procs = []
    procs.append(Process(target=player_proc, args=(queue,)))
    procs.append(Process(target=button_proc))
    procs.append(Process(target=timer_proc))
    for proc in procs:
        proc.start()
    # ロゴイメージをディスプレイに表示
    load_img(logo_img)
    # APIサーバを起動
    uvicorn.run(app, host="0.0.0.0", reload=False)
