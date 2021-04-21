#!/usr/bin/python3

import os.path, argparse, time, yaml, logging, logging.handlers
import paho.mqtt.client as mqtt

args = None
config = {}
defaultLogging = None
brokers = {}
topics = []

class DefaultLogging:

    def __init__(self, conf):
        self.root = conf.get('root', '/logs')
        self.format = conf.get('format', None)
        self.maxBytes = conf.get('maxBytes', 10000000)
        self.backupCount = conf.get('backupCount', 3)

        if type(self.maxBytes) is str:
            ch = self.maxBytes[-1].upper()
            num = int(self.maxBytes[:-1])
            if ch == 'K':
                num = num * 1000
            elif ch == 'M':
                num *= 1000000
            elif ch == 'G':
                num *= 1000000000
            else:
                raise ValueError('maxBytes suffix is unknown')
            self.maxBytes = num

    
class Broker:

    def __init__(self, conf):
        self.name = conf.get('name', None)
        self.address = conf.get('address', 'localhost')
        self.port = conf.get('port', 1883)
        self.username = conf.get('username', None)
        self.password = conf.get('password', None)
        self.client = None
        self.topics = []
        self.connected = False
        
        if self.name is None:
            raise ValueError('Broker name is required')
        if self.address is None:
            raise ValueError('Broker address is required')
            
    def connect(self):
        if self.client is not None:
            return
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
        if self.username is not None:
            self.client.username_pw_set(self.username, self.password)
        self.client.connect_async(self.address, self.port)
        self.client.loop_start()

    def disconnect(self):
        if self.client is None:
            return
        self.client.disconnect()
        self.client.loop_stop()
        self.client = None
        
    def subscribe(self, topic):
        while not self.connected:
            time.sleep(1)
        (result, mid) = self.client.subscribe(topic.topic, topic.qos)
        topic.subscribe_mid = mid
        self.client.message_callback_add(topic.topic, topic.on_message)
        self.topics.append(topic)
    
    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        print('Connected to {} ({}:{}) with result code {}'.format(self.name, self.address, self.port, rc))
        
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        print('Disconnected from {} ({}:{}) with result code {}'.format(self.name, self.address, self.port, rc))
        
    def on_subscribe(self, client, userdata, mid, granted_qos):
        for topic in self.topics:
            if mid == topic.subscribe_mid:
                print('Subscribed to {}:{} with qos {}'.format(self.name, topic.topic, granted_qos[0]))
                break
    
class Topic:

    def __init__(self, conf):
        self.topic = conf.get('topic', None)
        self.qos = conf.get('qos', 0)
        self.broker = conf.get('broker', None)
        self.encoding = conf.get('encoding', 'utf-8')
        self.log = conf.get('log', None)
        self.format = conf.get('format', defaultLogging.format)
        self.maxBytes = conf.get('maxBytes', defaultLogging.maxBytes)
        self.backupCount = conf.get('backupCount', defaultLogging.backupCount)
        self.subscribe_mid = None
        self.logger = None
        
        if self.topic is None:
            raise ValueError('Topic name is required')
        if self.broker is None:
            raise ValueError('Broker is required')
        if self.broker not in brokers:
            raise ValueError('Broker "{}" is not defined'.format(self.broker))

        self.broker = brokers[self.broker]
        
    def subscribe(self):
        self.logger = logging.getLogger('{}:{}'.format(self.broker.name, self.topic))
        self.logger.propagate = False
        self.logger.setLevel('INFO')
        
        formatter = logging.Formatter(fmt = self.format)
        
        handler = logging.handlers.RotatingFileHandler(
            self.log if os.path.isabs(self.log) else os.path.join(defaultLogging.root, self.log),
            maxBytes = self.maxBytes,
            backupCount = self.backupCount
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        
        self.broker.subscribe(self)
        
        
    def on_message(self, client, userdata, message):
        self.logger.info(message.payload.decode(self.encoding))


def loadConfiguration():
    global config, defaultLogging
    with open(args.config) as stream:
        config = yaml.full_load(stream)
        
    if 'logging' not in config:
        config['logging'] = {}
    defaultLogging = DefaultLogging(config['logging'])
    
    
def connectToBrokers():
    if 'brokers' not in config:
        raise Exception('No brokers are defined')
    for bc in config['brokers']:
        broker = Broker(bc)
        if broker.name in brokers:
            raise ValueError('Broker name "{}" is already defined'.format(broker.name))
        broker.connect()
        brokers[broker.name] = broker
        
def disconnectFromBrokers():
    for name, broker in brokers.items():
        broker.disconnect()
        
def subscribeToTopics():
    if 'topics' not in config:
        raise Exception('No topics are defined')
    for tc in config['topics']:
        topic = Topic(tc)
        topic.subscribe()
        topics.append(topic)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description = 'Log MQTT topics to files')
    parser.add_argument('--config', '-c', type=str, dest='config', default='/config/configuration.yaml', help='path to configuration file')
    
    args = parser.parse_args()
    loadConfiguration()
    connectToBrokers()
    subscribeToTopics()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        disconnectFromBrokers()
        


