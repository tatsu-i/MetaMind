import os
import csv
import time
import math
import pika
import json
from pythonosc import dispatcher
from pythonosc import osc_server
from datetime import datetime

#Network Variables
ip = "0.0.0.0"
port = 5000

#Muse Variables
hsi = [4,4,4,4]
hsi_string = ""
abs_waves = [-1,-1,-1,-1,-1]
rel_waves = [-1,-1,-1,-1,-1]

def publish(message, queue_name):
    exchange_name = "muse"
    credentials = pika.PlainCredentials("guest", "guest")
    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq", port=5672))
    channel = connection.channel()
    channel.exchange_declare(exchange_name, durable=False)
    channel.queue_declare(queue=queue_name, durable=False)
    channel.queue_bind(queue_name, exchange_name, queue_name)
    channel.basic_publish(
        exchange=exchange_name, routing_key=queue_name, body=json.dumps(message),
    )
    connection.close()

#デバイスの装着状態を計測するハンドラ
def hsi_handler(address: str,*args):
    global hsi, hsi_string
    hsi = args
    if ((args[0]+args[1]+args[2]+args[3])==4):
        hsi_string_new = "Muse Fit Good"
    else:
        hsi_string_new = "Muse Fit Bad on: "
        if args[0]!=1:
            hsi_string_new += "Left Ear. "
        if args[1]!=1:
            hsi_string_new += "Left Forehead. "
        if args[2]!=1:
            hsi_string_new += "Right Forehead. "
        if args[3]!=1:
            hsi_string_new += "Right Ear."        
    if hsi_string!=hsi_string_new:
        hsi_string = hsi_string_new
        print(hsi_string)
        message = {"ts": time.time(), "hsi": hsi}
        publish(message, "hsi")

# バッテリー情報を受け取るハンドラ
def battery_handler(address, *args):
    level, batt_voltage, adc_voltage, temp = args
    level = level / 100
    print(f"Battery level: {level}")

# 各脳波の平均を求めるハンドラ
def abs_handler(address: str,*args):
    global hsi, abs_waves, rel_waves
    wave = args[0][0]
    
    # tp9, af7, af8, tp10のうち1つ以上のセンサーが動作している場合のみ値を取得する
    if (hsi[0]==1 or hsi[1]==1 or hsi[2]==1 or hsi[3]==1):
        # フィルタされたデータを受け取る場合
        if (len(args)==2):
            abs_waves[wave] = args[1]
        # すべてのセンサーを使った計測
        if (len(args)==5):
            sumVals=0
            countVals=0            
            # 良好なセンサーのみから値を取得して平均をとる
            for i in [0,1,2,3]:
                if hsi[i]==1:
                    countVals+=1
                    sumVals+=args[i+1]
            abs_waves[wave] = sumVals/countVals
            
        rel_waves[wave] = math.pow(10,abs_waves[wave]) / (math.pow(10,abs_waves[0]) + math.pow(10,abs_waves[1]) + math.pow(10,abs_waves[2]) + math.pow(10,abs_waves[3]) + math.pow(10,abs_waves[4]))

        message = {"ts": time.time(), "abs_waves": abs_waves, "rel_waves": rel_waves, "hsi": hsi}
        publish(message, "waves")

# センサーの生データを受け取るハンドラ
def eeg_handler(address, tp9, af7, af8, tp10, aux, unknown):
    global hsi
    message = {"ts": time.time(), "tp9": tp9, "af7": af7, "af8": af8, "tp10": tp10, "aux": aux, "hsi": hsi}
    publish(message, "eeg")

# 集中状態の検知
def concen_handler(unused_addr, value):
    message = {"ts": time.time(), "concentration": value}
    publish(message, "concentration")
    return

def mellow_handler(unused_addr, value):
    message = {"ts": time.time(), "mellow": value}
    publish(message, "mellow")
    return

# 瞬きを検知
def blink_handler(unused_addr, blink):
    message = {"ts": time.time(), "blink": blink}
    publish(message, "blink")

# 歯ぎしりを検知
def jaw_clench_handler(unused_addr, jaw):
    message = {"ts": time.time(), "jaw": jaw}
    publish(message, "jaw")

def gyro_handler(address, *args):
    message = {"ts": time.time(), "gyro": list(args)}
    publish(message, "gyro")

def acc_handler(address, *args):
    message = {"ts": time.time(), "acc": list(args)}
    publish(message, "acc")

# PPGセンサーには、周囲光（Ambient）、赤外線（Infrared）、および赤（Red）の3つのチャネルがあります。
def ppg_handler(address, *args):
    message = {"ts": time.time(), "ppg": list(args)}
    publish(message, "ppg")

def marker_handler(address, button, pressed):
    button = button[0]
    message = {"ts": time.time(), "button": button}
    publish(message, "marker")

# 必要に応じて未確認のメッセージを処理します
def default_handler(address, *args):
    print(f"DEFAULT {address}: {args}")

def nop_handler(address, *args):
    pass

#Main
if __name__ == "__main__":
    #Init Muse Listeners    
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/muse/batt", battery_handler)
    dispatcher.map("/muse/eeg", eeg_handler)
    dispatcher.map("/muse/elements/delta_absolute", abs_handler,0)
    dispatcher.map("/muse/elements/theta_absolute", abs_handler,1)
    dispatcher.map("/muse/elements/alpha_absolute", abs_handler,2)
    dispatcher.map("/muse/elements/beta_absolute", abs_handler,3)
    dispatcher.map("/muse/elements/gamma_absolute", abs_handler,4)
    dispatcher.map("/muse/elements/horseshoe", hsi_handler)
    dispatcher.map("/muse/elements/blink", blink_handler)
    dispatcher.map("/muse/elements/jaw_clench", jaw_clench_handler)
    dispatcher.map("/muse/algorithm/concentration", nop_handler)
    dispatcher.map("/muse/algorithm/mellow", nop_handler)
    dispatcher.map("/muse/elements/touching_forehead", nop_handler)
    dispatcher.map("/muse/gyro", gyro_handler)
    dispatcher.map("/muse/acc", acc_handler)
    dispatcher.map("/muse/ppg", ppg_handler)
    dispatcher.map(f"/Marker/1", marker_handler, 1)
    dispatcher.map(f"/Marker/2", marker_handler, 2)
    dispatcher.map(f"/Marker/3", marker_handler, 3)
    dispatcher.map(f"/Marker/4", marker_handler, 4)
    dispatcher.map(f"/Marker/5", marker_handler, 5)
    dispatcher.set_default_handler(default_handler)
    # start server
    server = osc_server.ThreadingOSCUDPServer((ip, port), dispatcher)
    print("Listening on UDP port "+str(port))
    server.serve_forever()
