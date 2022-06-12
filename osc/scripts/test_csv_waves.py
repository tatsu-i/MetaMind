import os
import time
import pika
import json
import sys
import csv

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

# message_waves = {
  # 'ts': 1650989509.9243116,
  # 'abs_waves': [0.5516904592514038, 0.20240004360675812, 0.5775450468063354, 0.540066659450531, 0.1230539008975029],
  # 'rel_waves': [0.2611048490622965, 0.1162378974596438, 0.2761196778099008, 0.2554734935902067, 0.09667933840996497],
  # 'hsi': [1,1,1,1]
# }

with open(sys.argv[1]) as f:
    reader = csv.reader(f)
    for row in reader:
        ts = float(row[0])
        abs_waves = list(map(float, row[1:6]))
        rel_waves = list(map(float, row[6:11]))
        message = {"ts": ts, "abs_waves": abs_waves, "rel_waves": rel_waves, "hsi": [1, 1, 1, 1]}
        publish(message, "waves")
