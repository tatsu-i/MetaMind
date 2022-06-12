import os
import time
import pika
import json

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

message_waves = {
  'ts': 1650989509.9243116,
  'abs_waves': [0.5516904592514038, 0.20240004360675812, 0.5775450468063354, 0.540066659450531, 0.1230539008975029],
  'rel_waves': [0.2611048490622965, 0.1162378974596438, 0.2761196778099008, 0.2554734935902067, 0.09667933840996497],
  'hsi': [1,1,1,1]
}
message_eeg = {"ts": 1650989509.9243116, "tp9": 814.3223266601562, "af7": 757.5091552734375, "af8": 795.7875366210938, "tp10": 839.7069702148438, "aux": 839.7069702148438, 'hsi': [1,1,1,1]}
message_blink = {"ts": 1650989509.9243116, "blink": 1}
message_jaw = {"ts": 1650989509.9243116, "jaw": 1}
message_hsi = {"ts": 1650989509.9243116, "hsi": [1,1,1,1]}
message_button = {"ts": 1650989509.9243116, "button": [1,1,1,1,1]}

for i in range(100):
    publish(message_waves, "waves")
    publish(message_eeg, "eeg")
    publish(message_blink, "blink")
    publish(message_jaw, "jaw")
    publish(message_hsi, "hsi")
    publish(message_button, "button")
