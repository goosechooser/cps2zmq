# pylint: disable=E1101

import time
import pytest
import zmq
import msgpack


class MockClient():
    def __init__(self, pushto):
        self._context = zmq.Context.instance()

        self._pusher = self._context.socket(zmq.PUSH)
        self._pusher.bind(pushto)
        self._pusher.setsockopt(zmq.LINGER, 0)

    @property
    def pusher(self):
        return self._pusher

    def close(self):
        self._pusher.close()

    def push_messages(self, messages):
        messages.append({'frame_number': 'closing', 'sprites': [], 'palettes': []})
        for msg in messages:
            packed = msgpack.packb(msg)
            self._pusher.send(packed)


class MockSink():
    def __init__(self, pullfrom):
        self._context = zmq.Context.instance()

        self._puller = self._context.socket(zmq.PULL)
        self._puller.bind(pullfrom)
        self._puller.setsockopt(zmq.LINGER, 0)

        self._control = self._context.socket(zmq.PUB)
        self._control.bind("inproc://mockcontrol")

    def run(self, num_messages):
        msgs_recv = 0
        messages = []

        while msgs_recv != num_messages:
            recv = self._puller.recv_pyobj()
            if recv['message'] == 'closing':
                self._control.send_string('KILL')
            else:
                messages.append(recv['message'])
                msgs_recv += 1

        return messages

    def close(self):
        self._control.close()
        self._puller.close()

class MockWorker():
    def __init__(self, wid=None, pullfrom=None, context=None):
        self._context = context or zmq.Context.instance()
        self._wid = wid
        self._pusher = self._context.socket(zmq.PUSH)
        self._pusher.connect("inproc://frommockworkers")

    @property
    def wid(self):
        return self._wid

    @wid.setter
    def wid(self, value):
        self._wid = value

    def run(self):
        pass

    def close(self):
        self._pusher.close()

class MockServer():
    def __init__(self, port, context=None):
        self._context = context or zmq.Context.instance()
        self._subscriber = self._context.socket(zmq.SUB)
        self._subscriber.connect(':'.join(["tcp://localhost", str(port)]))
        self._subscriber.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        print("starting server")

        message = 'ok'
        # while message != "closing":
        for i in range(10):
            message = self._subscriber.recv()
            # print('message', message)
            # print('message type', type(message))

            message = msgpack.unpackb(message, encoding='utf-8')
            print('frame number', message['frame_number'])
            # print('palettes', message['palettes'])
            print('sprites', message['sprites'])
            print('type o sprites', type(message['sprites']))

            message = message['frame_number']
            # print(message)
        print('donezo')

    def close(self):
        self._subscriber.close()

@pytest.fixture(scope="module")
def client():
    client = MockClient("inproc://toworkers")
    yield client
    client.close()


@pytest.fixture(scope="module")
def sink():
    sink = MockSink("inproc://mockworkers")
    yield sink
    sink.close()

@pytest.fixture(scope="module")
def worker():
    worker = MockWorker()
    yield worker
    worker.close()

@pytest.fixture(scope="module")
def workers():
    workers = [MockWorker(wid=num) for num in range(1, 3)]
    yield workers
    for w in workers:
        w.close()

@pytest.fixture(scope="module")
def server():
    server = MockServer(5556)
    yield server
    server.close()
