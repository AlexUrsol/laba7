import threading

import pika
from flask import Flask
import sys
import consul

app = Flask(__name__)

CONSUL_SERVER_ADDR = "consul-server"
ALL_TIME_MESSAGES_11 = []



def register_service(id, port):
    c = consul.Consul(host=CONSUL_SERVER_ADDR)
    check_http = consul.Check.http(f'http://messager_{id}:{port}/health', interval='10s')
    c.agent.service.register(
        'messager',
        service_id=f'messager_{id}',
        address=f"messager_{id}",
        port=port,
        check=check_http,
    )

@app.route('/health', methods=['GET'])
def health():
    return app.response_class(status=200)


def get_kv(c, name):
    return c.kv.get(name)[1]['Value'].decode()


@app.route('/messages',  methods=['GET'])
def messages():
        print(ALL_TIME_MESSAGES_11)
        return str(ALL_TIME_MESSAGES_11)


def threaded(fn):
    def run(*args, **kwargs):
        t = threading.Thread(target=fn, args=args, kwargs=kwargs)
        t.start()
        return t
    return run

@threaded
def consuming():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq')
    )
    channel = connection.channel()
    c = consul.Consul(host=CONSUL_SERVER_ADDR)
    q = get_kv(c, "queue")
    channel.queue_declare(queue=q)
    for method_frame, properties, body in channel.consume(q):
        print("ACCEPTED %r" % body)
        print('early: ', ALL_TIME_MESSAGES_11)
        ALL_TIME_MESSAGES_11.append(str(body))
        print('Now ', ALL_TIME_MESSAGES_11)

if __name__ == '__main__':
    port = 1122
    id = int(sys.argv[1])
    consuming()
    register_service(id, port)
    print('LETS GO 1')
    app.run(host='0.0.0.0', port=port, debug=False)

