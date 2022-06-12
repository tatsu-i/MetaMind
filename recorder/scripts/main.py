import os
import csv
import time
import pika
import json
import traceback
from datetime import datetime
from multiprocessing import Process
import pandas as pd
import requests

def play_sound(rpi_host, stage):
    url = f"http://{rpi_host}:8000/sleep/{stage}"
    requests.get(url)

def stop_sound(rpi_host):
    url = f"http://{rpi_host}:8000/stop"
    requests.get(url)

RPI_HOST = os.environ.get("RPI_HOST", "0.0.0.0")
SAMPLE_NAME = os.environ.get("SAMPLE_NAME", "test")
file_timestamp = datetime.now().strftime("%Y-%m-%d")
LOG_DIR = os.path.join("/logs", f"{SAMPLE_NAME}-{file_timestamp}")
try:
    os.makedirs(LOG_DIR)
except:
    pass

SAMPLE_RATE = 20 # 秒間に受け取るデータ量
FETCH_MAX_SIZE = 10 * SAMPLE_RATE
fetch_count = 0
stage = "wakeup"

def predict_sleep_stage(waves_file_name):
    stage = "wakeup"
    try:
        header = ["ts", "abs_delta", "abs_theta", "abs_alpha", "abs_beta", "abs_gamma", "rel_delta", "rel_theta", "rel_alpha", "rel_beta", "rel_gamma", "hsi"]
        df = pd.read_csv(waves_file_name, names=header)
        df["ts"] = df["ts"] - df.iloc[0]["ts"]
        df = df.set_index("ts")
        # 直近10分のみ取得
        df = df.head(-600*SAMPLE_RATE)
        df["offset"] = df["rel_delta"] - df["rel_alpha"]
        # 移動平均を求める
        df["offset"] = df["offset"].rolling(600*SAMPLE_RATE).mean()
        df = df.dropna()
        df_offset = df.loc[:,["offset"]]
        offset = df_offset.iloc[-1]["offset"]
        if -0.2 < offset < 0.25:
            stage = "rem"
        if offset > 0.25:
            stage = "nonrem"
    except Exception as e:
        print(e)
    return stage

def subscribe(queue_name, callback, auto_ack=False):
    while True:
        exchange = "muse"
        credentials = pika.PlainCredentials("guest", "guest")
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq", port=5672))
        channel = connection.channel()
        channel.exchange_declare(exchange, durable=False)
        channel.queue_declare(queue=queue_name, durable=False)
        channel.queue_bind(queue_name, exchange, queue_name)
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=auto_ack)
        channel.start_consuming()
        connection.close()
        time.sleep(1)

def callback_button(ch, method, properties, body):
    # {"ts": 1650989509.9243116, "button": [0,0,1,1,0]}
    body = json.loads(body)
    line = [body["ts"]] + body["button"]
    with open(f'{LOG_DIR}/button.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_waves(ch, method, properties, body):
    # delta: 0, theta: 1, alpha: 2, beta: 3, gamma: 4
    # {
    #   'ts': 1650989509.9243116,
    #   'abs_waves': [0.5516904592514038, 0.20240004360675812, 0.5775450468063354, 0.540066659450531, 0.1230539008975029],
    #   'rel_waves': [0.2611048490622965, 0.1162378974596438, 0.2761196778099008, 0.2554734935902067, 0.09667933840996497],
    #   'hsi': [1,1,1,1]
    # }
    body = json.loads(body)
    waves_file_name = f'{LOG_DIR}/waves.csv'
    global fetch_count, stage
    fetch_count += 1
    try:
        ts = body["ts"]
        if fetch_count > FETCH_MAX_SIZE:
            fetch_count = 0
            current_stage = predict_sleep_stage(waves_file_name)
            now = datetime.fromtimestamp(ts).isoformat()
            if current_stage != stage:
                stage = current_stage
                print(now, stage)
                play_sound(RPI_HOST, stage)
        hsi = body["hsi"]
        line = [ts] + body["abs_waves"] + body["rel_waves"] + [sum(hsi)]
        with open(waves_file_name, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(line)
    except Exception as e:
        print(traceback.format_exc())
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_eeg(ch, method, properties, body):
    # {"ts": 1650989509.9243116, "tp9": 814.3223266601562, "af7": 757.5091552734375, "af8": 795.7875366210938, "tp10": 839.7069702148438, "aux": 839.7069702148438, "hsi": [1,1,1,1]}
    try:
        body = json.loads(body)
        hsi = body["hsi"]
        line = [body["ts"], body["tp9"], body["af7"], body["af8"], body["tp10"], body["aux"], sum(hsi)]
        with open(f'{LOG_DIR}/eeg.csv', 'a') as f:
            writer = csv.writer(f)
            writer.writerow(line)
    except Exception as e:
        print(traceback.format_exc())
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_blink(ch, method, properties, body):
    # {"ts": 1650989509.9243116, "blink": 1}
    body = json.loads(body)
    line = [body["ts"] , body["blink"]]
    with open(f'{LOG_DIR}/blink.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_jaw(ch, method, properties, body):
    # {"ts": 1650989509.9243116, "jaw": 1}
    body = json.loads(body)
    line = [body["ts"] , body["jaw"]]
    with open(f'{LOG_DIR}/jaw.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_hsi(ch, method, properties, body):
    # {"ts": 1650989509.9243116, "hsi": [1,1,1,1]}
    body = json.loads(body)
    line = [body["ts"]] + body["hsi"]
    with open(f'{LOG_DIR}/hsi.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_acc(ch, method, properties, body):
    body = json.loads(body)
    line = [body["ts"]] + body["acc"]
    with open(f'{LOG_DIR}/acc.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_gyro(ch, method, properties, body):
    body = json.loads(body)
    line = [body["ts"]] + body["gyro"]
    with open(f'{LOG_DIR}/gyro.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_ppg(ch, method, properties, body):
    body = json.loads(body)
    line = [body["ts"]] + body["ppg"]
    with open(f'{LOG_DIR}/ppg.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow(line)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def callback_marker(ch, method, properties, body):
    body = json.loads(body)
    button = body["button"]
    print(f"button {button} pressed.")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_proc():
    proc = []
    proc.append(Process(target=subscribe, args=("waves", callback_waves,)))
    proc.append(Process(target=subscribe, args=("blink", callback_blink,)))
    proc.append(Process(target=subscribe, args=("jaw", callback_jaw,)))
    proc.append(Process(target=subscribe, args=("eeg", callback_eeg,)))
    proc.append(Process(target=subscribe, args=("hsi", callback_hsi,)))
    proc.append(Process(target=subscribe, args=("button", callback_button,)))
    proc.append(Process(target=subscribe, args=("acc", callback_acc,)))
    proc.append(Process(target=subscribe, args=("gyro", callback_gyro,)))
    proc.append(Process(target=subscribe, args=("ppg", callback_ppg,)))
    proc.append(Process(target=subscribe, args=("marker", callback_marker,)))
    for p in proc:
        p.start()
    return proc

def stop_proc(proc):
    for p in proc:
        p.kill()

proc = start_proc()

while True:
    time.sleep(1)
