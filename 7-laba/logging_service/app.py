import hazelcast
from flask import Flask, request
import sys
import consul


app = Flask(__name__)

CONSUL_SERVER_ADDR = "consul-server"

def register_service(consul_client, id, port):
    check_http = consul.Check.http(f'http://logging_service_{id}:{port}/health', interval='10s')
    consul_client.agent.service.register(
        'logging_service',
        service_id=f'logging_service_{id}',
        address=f"logging_service_{id}",
        port=port,
        check=check_http,
    )


@app.route('/health', methods=['GET'])
def health():
    return app.response_class(status=200)


def get_kv(c, name):
    return c.kv.get(name)[1]['Value'].decode()


@app.route('/logging-service', methods=['POST'])
def logger_post():
    m = get_kv(consul_client, 'map')
    print(f'\n --- post request from facade --- \n {request.json}\n')
    distributed_map = client.get_map(m)
    distributed_map.set(str(request.json['uuid']), str(request.json['message']))
    print('--- SUCCESSFULLY SAVED ---')
    return app.response_class(status=200)

@app.route('/logging-service', methods=['GET'])
def logger_get():
    m = get_kv(consul_client, 'map')
    distributed_map = client.get_map(m)
    messages = distributed_map.values().result()
    print('\n --- get request from facade --- \n')
    return ','.join([msg for msg in messages]) or ''


if __name__ == '__main__':
    id = int(sys.argv[1])
    port = 8011
    consul_client = consul.Consul(host=CONSUL_SERVER_ADDR)
    client = hazelcast.HazelcastClient(
        cluster_name=get_kv(consul_client, 'cluster'),
        cluster_members=get_kv(consul_client, "hazelcast_addrs").split(',')
    )
    register_service(consul_client, id, port)
    app.run(host='0.0.0.0', port=port, debug=True)

