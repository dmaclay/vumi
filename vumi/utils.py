# -*- test-case-name: vumi.tests.test_utils -*-

import os.path
import re

import importlib
from zope.interface import implements
from twisted.internet import defer
from twisted.internet import reactor, protocol
from twisted.internet.defer import succeed
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer


def http_request(url, data, headers={}, method='POST'):
    # Construct an Agent.
    agent = Agent(reactor)

    d = agent.request(method,
                      url,
                      Headers(headers),
                      StringProducer(data) if data else None)

    def handle_response(response):
        if response.code == 204:
            d = defer.succeed('')
        else:
            class SimpleReceiver(protocol.Protocol):
                def __init__(s, d):
                    s.buf = ''
                    s.d = d

                def dataReceived(s, data):
                    s.buf += data

                def connectionLost(s, reason):
                    # TODO: test if reason is twisted.web.client.ResponseDone,
                    # if not, do an errback
                    s.d.callback(s.buf)

            d = defer.Deferred()
            response.deliverBody(SimpleReceiver(d))
        return d

    d.addCallback(handle_response)
    return d


def normalize_msisdn(raw, country_code=''):
    # don't touch shortcodes
    if len(raw) <= 5:
        return raw

    raw = ''.join([c for c in str(raw) if c.isdigit() or c == '+'])
    if raw.startswith('00'):
        return '+' + raw[2:]
    if raw.startswith('0'):
        return '+' + country_code + raw[1:]
    if raw.startswith('+'):
        return raw
    if raw.startswith(country_code):
        return '+' + raw
    return raw


class StringProducer(object):
    """
    For various twisted.web mechanics we need a producer to produce
    content for HTTP requests, this is a helper class to quickly
    create a producer for a bit of content
    """
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


def make_vumi_path_abs(path):
    """
    Return an absolute path by prepending the vumi "root" directory.

    The "root" directory is the one containing the "vumi" package. If
    the path is already absolute, it is returned as-is.
    """
    if os.path.isabs(path):
        return path
    # We know where this file is relative to the vumi "root"
    this_path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(this_path, path)


def load_class(module_name, class_name):
    """
    Load a class when given its module and its class name

    >>> load_class('vumi.workers.example','ExampleWorker') # doctest: +ELLIPSIS
    <class vumi.workers.example.ExampleWorker at ...>
    >>>

    """
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def load_class_by_string(class_path):
    """
    Load a class when given it's full name, including modules in python
    dot notation

    >>> cls = 'vumi.workers.example.ExampleWorker'
    >>> load_class_by_string(cls) # doctest: +ELLIPSIS
    <class vumi.workers.example.ExampleWorker at ...>
    >>>

    """
    parts = class_path.split('.')
    module_name = '.'.join(parts[:-1])
    class_name = parts[-1]
    return load_class(module_name, class_name)


def filter_options_on_prefix(options, prefix, delimiter='-'):
    """
    splits an options dict based on key prefixes

    >>> filter_options_on_prefix({'foo-bar-1': 'ok'}, 'foo')
    {'bar-1': 'ok'}
    >>>

    """
    return dict((key.split(delimiter, 1)[1], value)
                for key, value in options.items()
                if key.startswith(prefix))


def cleanup_msisdn(number, country_code):
    number = re.sub('\+', '', number)
    number = re.sub('^0', country_code, number)
    return number


def get_operator_name(msisdn, mapping):
    for key, value in mapping.items():
        if msisdn.startswith(str(key)):
            if isinstance(value, dict):
                return get_operator_name(msisdn, value)
            return value
    return 'UNKNOWN'


def get_operator_number(msisdn, country_code, mapping, numbers):
    msisdn = cleanup_msisdn(msisdn, country_code)
    operator = get_operator_name(msisdn, mapping)
    number = numbers.get(operator)
    return number


def safe_routing_key(routing_key):
    """
    >>> safe_routing_key(u'*32323#')
    u's32323h'
    >>>

    """
    return reduce(lambda r_key, kv: r_key.replace(*kv),
                    [('*', 's'), ('#', 'h')], routing_key)


### SAMPLE CONFIG PARAMETERS - REPLACE 'x's IN OPERATOR_NUMBER

"""
COUNTRY_CODE: "27"

OPERATOR_NUMBER:
    VODACOM: "2782xxxxxxxxxxx"
    MTN: "2783xxxxxxxxxxx"
    CELLC: "2784xxxxxxxxxxx"
    VIRGIN: ""
    8TA: ""
    UNKNOWN: ""

OPERATOR_PREFIX:
    2771:
        27710: MTN
        27711: VODACOM
        27712: VODACOM
        27713: VODACOM
        27714: VODACOM
        27715: VODACOM
        27716: VODACOM
        27717: MTN
        27719: MTN

    2772: VODACOM
    2773: MTN
    2774:
        27740: CELLC
        27741: VIRGIN
        27742: CELLC
        27743: CELLC
        27744: CELLC
        27745: CELLC
        27746: CELLC
        27747: CELLC
        27748: CELLC
        27749: CELLC

    2776: VODACOM
    2778: MTN
    2779: VODACOM
    2781:
        27811: 8TA
        27812: 8TA
        27813: 8TA
        27814: 8TA

    2782: VODACOM
    2783: MTN
    2784: CELLC

"""


def get_deploy_int(deployment):
    lookup = {
        "develop": 7,
        "/develop": 7,
        "development": 7,
        "/development": 7,
        "production": 8,
        "/production": 8,
        "staging": 9,
        "/staging": 9,
        "qa": 9,
        "/qa": 9,
        }
    return lookup.get(deployment.lower(), 7)
