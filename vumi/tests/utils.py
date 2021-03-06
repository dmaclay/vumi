# -*- test-case-name: vumi.tests.test_testutils -*-

import re
import json
import importlib
import fnmatch
from datetime import datetime, timedelta
from collections import namedtuple
from contextlib import contextmanager

import pytz
from twisted.internet import defer

from vumi.utils import make_vumi_path_abs
from vumi.service import get_spec, Worker
from vumi.tests.fake_amqp import FakeAMQClient


def setup_django_test_database():
    from django.test.simple import DjangoTestSuiteRunner
    from django.test.utils import setup_test_environment
    from south.management.commands import patch_for_test_db_setup
    runner = DjangoTestSuiteRunner(verbosity=0, failfast=False)
    patch_for_test_db_setup()
    setup_test_environment()
    return runner, runner.setup_databases()


def teardown_django_test_database(runner, config):
    from django.test.utils import teardown_test_environment
    runner.teardown_databases(config)
    teardown_test_environment()


class UTCNearNow(object):
    def __init__(self, offset=10):
        self.now = datetime.utcnow()
        self.utcnow = self.now.replace(tzinfo=pytz.UTC)
        self.offset = timedelta(offset)

    def __eq__(self, other):
        now = self.now
        if other.tzinfo:
            now = self.utcnow
        return (now - self.offset) < other < (now + self.offset)


class RegexMatcher(object):
    def __init__(self, regex):
        self.regex = re.compile(regex)

    def __eq__(self, other):
        return self.regex.match(other)


class Mocking(object):

    class HistoryItem(object):
        def __init__(self, args, kwargs):
            self.args = args
            self.kwargs = kwargs

    def __init__(self, function):
        """Mock a function"""
        self.function = function
        self.called = 0
        self.history = []
        self.return_value = None

    def __enter__(self):
        """Overwrite whatever module the function is part of"""
        self.mod = importlib.import_module(self.function.__module__)
        setattr(self.mod, self.function.__name__, self)
        return self

    def __exit__(self, *exc_info):
        """Reset to whatever the function was originally when done"""
        setattr(self.mod, self.function.__name__, self.function)

    def __call__(self, *args, **kwargs):
        """Return the return value when called, store the args & kwargs
        for testing later, called is a counter and evaluates to True
        if ever called."""
        self.args = args
        self.kwargs = kwargs
        self.called += 1
        self.history.append(self.HistoryItem(args, kwargs))
        return self.return_value

    def to_return(self, *args):
        """Specify the return value"""
        self.return_value = args if len(args) > 1 else list(args).pop()
        return self


def mocking(fn):
    return Mocking(fn)


class TestPublisher(object):
    """
    A test publisher that caches outbound messages in an internal queue
    for testing, instead of publishing over AMQP.

    Useful for testing consumers
    """
    def __init__(self):
        self.queue = []

    @contextmanager
    def transaction(self):
        yield

    def publish_message(self, message, **kwargs):
        self.queue.append((message, kwargs))


def fake_amq_message(dictionary, delivery_tag='delivery_tag'):
    Content = namedtuple('Content', ['body'])
    Message = namedtuple('Message', ['content', 'delivery_tag'])
    return Message(delivery_tag=delivery_tag,
                   content=Content(body=json.dumps(dictionary)))


class TestQueue(object):
    """
    A test queue that mimicks txAMQP's queue behaviour (DEPRECATED)
    """
    def __init__(self, queue, fake_broker=None):
        self.queue = queue
        self.fake_broker = fake_broker
        # TODO: Hook this up.

    def push(self, item):
        self.queue.append(item)

    def get(self):
        d = defer.Deferred()
        if self.queue:
            d.callback(self.queue.pop())
        return d


class TestChannel(object):
    "(DEPRECATED)"

    def __init__(self, channel_id=None, fake_broker=None):
        self.channel_id = channel_id
        self.fake_broker = fake_broker
        self.ack_log = []
        self.publish_log = []
        self.publish_message_log = self.publish_log  # TODO: Nuke

    def basic_ack(self, tag, multiple=False):
        self.ack_log.append((tag, multiple))

    def channel_close(self, *args, **kwargs):
        return defer.succeed(None)

    def channel_open(self, *args, **kwargs):
        return defer.succeed(None)

    def basic_publish(self, *args, **kwargs):
        self.publish_log.append(kwargs)
        if self.fake_broker:
            self.fake_broker.publish(**kwargs)

    def basic_qos(self, *args, **kwargs):
        return defer.succeed(None)

    def exchange_declare(self, *args, **kwargs):
        if self.fake_broker:
            self.fake_broker.exchange_declare(*args, **kwargs)

    def queue_declare(self, *args, **kwargs):
        if self.fake_broker:
            self.fake_broker.queue_declare(*args, **kwargs)

    def queue_bind(self, *args, **kwargs):
        if self.fake_broker:
            self.fake_broker.queue_bind(*args, **kwargs)

    def basic_consume(self, queue, **kwargs):
        return namedtuple('Reply', ['consumer_tag'])(consumer_tag=queue)

    def close(self, *args, **kwargs):
        return True


def get_stubbed_worker(worker_class, config=None, broker=None):
    spec = get_spec(make_vumi_path_abs("config/amqp-spec-0-8.xml"))
    amq_client = FakeAMQClient(spec, {}, broker)
    worker = worker_class(amq_client, config)
    return worker


def get_stubbed_channel(broker=None, id=0):
    spec = get_spec(make_vumi_path_abs("config/amqp-spec-0-8.xml"))
    amq_client = FakeAMQClient(spec, {}, broker)
    return amq_client.channel(id)


class TestResourceWorker(Worker):
    port = 9999
    _resources = ()

    def set_resources(self, resources):
        self._resources = resources

    def startWorker(self):
        resources = [(cls(*args), path) for path, cls, args in self._resources]
        self.resources = self.start_web_resources(resources, self.port)
        return defer.succeed(None)

    def stopWorker(self):
        if self.resources:
            self.resources.stopListening()


class FakeRedis(object):
    def __init__(self):
        self._data = {}

    # Global operations

    def exists(self, key):
        return key in self._data

    def keys(self, pattern='*'):
        return fnmatch.filter(self._data.keys(), pattern)

    def flushdb(self):
        self._data = {}

    # String operations

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value):
        value = str(value)  # set() sets string value
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)

    # Hash operations

    def hmset(self, key, mapping):
        hval = self._data.setdefault(key, {})
        hval.update(mapping)

    def hgetall(self, key):
        return self._data.get(key, {})

    # Set operations

    def sadd(self, key, value):
        sval = self._data.setdefault(key, set())
        sval.add(value)

    def smembers(self, key):
        return self._data.get(key, set())

    def spop(self, key):
        sval = self._data.get(key, set())
        if not sval:
            return None
        return sval.pop()

    def scard(self, key):
        return len(self._data.get(key, set()))

    # Sorted set operations

    def zadd(self, key, **valscores):
        zval = self._data.setdefault(key, [])
        new_zval = [val for val in zval if val[1] not in valscores]
        for value, score in valscores.items():
            new_zval.append((score, value))
        new_zval.sort()
        self._data[key] = new_zval

    def zrem(self, key, value):
        zval = self._data.setdefault(key, [])
        new_zval = [val for val in zval if val[1] != value]
        self._data[key] = new_zval

    def zcard(self, key):
        return len(self._data.get(key, []))

    def zrange(self, key, start, stop):
        zval = self._data.get(key, [])
        stop += 1  # redis start/stop are element indexes
        if stop == 0:
            stop = None
        return [val[1] for val in zval[start:stop]]
