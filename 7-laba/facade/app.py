import random
import uuid
import pika
import time
import requests
import consul
from flask import Flask, request

app = Flask(__name__)


CONSUL_SERVER_ADDR = "consul-server"

def register_service(consul_client, port):
    check_http = consul.Check.http(f'http://facade:{port}/health', interval='10s')
    consul_client.agent.service.register(
        'facade',
        service_id=f'facade_service',
        address="facade",
        port=port,
        check=check_http,
    ) 


def get_kv(c, name):
    return c.kv.get(name)[1]['Value'].decode()


def discover_service(name):
    services = []
    while not services:
        for s in consul_client.health.service(name, passing=True)[1]:
            info = s['Service']
            services.append(f"{info['Address']}:{info['Port']}")
        if services:
            break
        time.sleep(2)
    return random.choice(services)


def get_rand_logging_client():
    return f'http://{discover_service("logging_service")}/logging-service'

def get_rand_messages_service_url() -> str:
    return f'http://{discover_service("messager")}/messages'

@app.route('/facade-service', methods=['POST'])
def facade_service_post():
    post_msg_to_mq(request.json.get('message'))
    logging_service_response = requests.post(
        url=get_rand_logging_client(),
        json={
            "uuid": str(uuid.uuid4()),
            "message": request.json.get('message')
        }
    )
    status = logging_service_response.status_code
    return app.response_class(status=status)

@app.route('/facade-service', methods=['GET'])
def facade_service_get():
    logging_service_response = requests.get(get_rand_logging_client())
    messages_service_r = requests.get(get_rand_messages_service_url())
    return str(logging_service_response.text) + ' : ' + str(messages_service_r.text)

@app.route('/health', methods=['GET'])
def health():
    return app.response_class(status=200)

def post_msg_to_mq(msg: str):
    mq_connection = pika.BlockingConnection(
        pika.ConnectionParameters(get_kv(consul_client, "rabbit_host"))
    )
    channel = mq_connection.channel()
    queue = get_kv(consul_client, "queue")
    channel.queue_declare(queue=queue)
    channel.basic_publish(
        exchange='', routing_key=queue,
        body=msg,
    )
    print(f"[x] Sent: {msg}")
    mq_connection.close()


if __name__ == '__main__':
    port = 1345
    consul_client = consul.Consul(host=CONSUL_SERVER_ADDR)
    register_service(consul_client, port)
    app.run(host='0.0.0.0', port=port, debug=True)
