from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks, Deferred

from vumi.service import get_spec, Worker
from vumi.utils import make_vumi_path_abs
from vumi.tests import fake_amqp


def mkmsg(body):
    return fake_amqp.Thing("Message", body=body)


class FakeAMQPTestCase(TestCase):
    def setUp(self):
        self.broker = fake_amqp.FakeAMQPBroker()

    def make_exchange(self, exchange, exchange_type):
        self.broker.exchange_declare(exchange, exchange_type)
        return self.broker.exchanges[exchange]

    def make_queue(self, queue):
        self.broker.queue_declare(queue)
        return self.broker.queues[queue]

    def make_channel(self, channel_id, delegate=None):
        channel = fake_amqp.FakeAMQPChannel(channel_id, self.broker, delegate)
        channel.channel_open()
        return channel

    def set_up_broker(self):
        self.chan1 = self.make_channel(1)
        self.chan2 = self.make_channel(2)
        self.ex_direct = self.make_exchange('direct', 'direct')
        self.ex_topic = self.make_exchange('topic', 'topic')
        self.q1 = self.make_queue('q1')
        self.q2 = self.make_queue('q2')
        self.q3 = self.make_queue('q3')

    def test_misc(self):
        str(fake_amqp.Thing('kind', foo='bar'))
        msg = fake_amqp.Message(None, [('foo', 'bar')])
        self.assertEqual('bar', msg.foo)
        self.assertRaises(AttributeError, lambda: msg.bar)

    def test_channel_open(self):
        channel = fake_amqp.FakeAMQPChannel(0, self.broker, None)
        self.assertEqual([], self.broker.channels)
        channel.channel_open()
        self.assertEqual([channel], self.broker.channels)

    def test_exchange_declare(self):
        channel = self.make_channel(0)
        self.assertEqual({}, self.broker.exchanges)
        channel.exchange_declare('foo', 'direct')
        self.assertEqual(['foo'], self.broker.exchanges.keys())
        self.assertEqual('direct', self.broker.exchanges['foo'].exchange_type)
        channel.exchange_declare('bar', 'topic')
        self.assertEqual(['bar', 'foo'], sorted(self.broker.exchanges.keys()))
        self.assertEqual('topic', self.broker.exchanges['bar'].exchange_type)

    def test_declare_and_queue_bind(self):
        channel = self.make_channel(0)
        self.assertEqual({}, self.broker.queues)
        channel.queue_declare('foo')
        channel.queue_declare('foo')
        self.assertEqual(['foo'], self.broker.queues.keys())
        exch = self.make_exchange('exch', 'direct')
        self.assertEqual({}, exch.binds)
        channel.queue_bind('foo', 'exch', 'routing.key')
        self.assertEqual(['routing.key'], exch.binds.keys())

        n = len(self.broker.queues)
        channel.queue_declare('')
        self.assertEqual(n + 1, len(self.broker.queues))

    def test_publish_direct(self):
        self.set_up_broker()
        self.chan1.queue_bind('q1', 'direct', 'routing.key.one')
        self.chan1.queue_bind('q1', 'direct', 'routing.key.two')
        self.chan1.queue_bind('q2', 'direct', 'routing.key.two')
        delivered = []

        def fake_put(*args):
            delivered.append(args)
        self.q1.put = fake_put
        self.q2.put = fake_put
        self.q3.put = fake_put

        self.chan1.basic_publish('direct', 'routing.key.none', 'blah')
        self.assertEqual([], delivered)

        self.chan1.basic_publish('direct', 'routing.key.*', 'blah')
        self.assertEqual([], delivered)

        self.chan1.basic_publish('direct', 'routing.key.#', 'blah')
        self.assertEqual([], delivered)

        self.chan1.basic_publish('direct', 'routing.key.one', 'blah')
        self.assertEqual([('direct', 'routing.key.one', 'blah')], delivered)

        delivered[:] = []  # Clear without reassigning
        self.chan1.basic_publish('direct', 'routing.key.two', 'blah')
        self.assertEqual([('direct', 'routing.key.two', 'blah')] * 2,
                         delivered)

    def test_publish_topic(self):
        self.set_up_broker()
        self.chan1.queue_bind('q1', 'topic', 'routing.key.*.foo.#')
        self.chan1.queue_bind('q2', 'topic', 'routing.key.#.foo')
        self.chan1.queue_bind('q3', 'topic', 'routing.key.*.foo.*')
        delivered = []

        def mfp(q):
            def fake_put(*args):
                delivered.append((q,) + args)
            return fake_put
        self.q1.put = mfp('q1')
        self.q2.put = mfp('q2')
        self.q3.put = mfp('q3')

        self.chan1.basic_publish('topic', 'routing.key.none', 'blah')
        self.assertEqual([], delivered)

        self.chan1.basic_publish('topic', 'routing.key.foo.one', 'blah')
        self.assertEqual([], delivered)

        self.chan1.basic_publish('topic', 'routing.key.foo', 'blah')
        self.assertEqual([('q2', 'topic', 'routing.key.foo', 'blah')],
                         delivered)

        delivered[:] = []  # Clear without reassigning
        self.chan1.basic_publish('topic', 'routing.key.one.two.foo', 'blah')
        self.assertEqual([('q2', 'topic', 'routing.key.one.two.foo', 'blah')],
                         delivered)

        delivered[:] = []  # Clear without reassigning
        self.chan1.basic_publish('topic', 'routing.key.one.foo', 'blah')
        self.assertEqual([('q1', 'topic', 'routing.key.one.foo', 'blah'),
                          ('q2', 'topic', 'routing.key.one.foo', 'blah'),
                          ], sorted(delivered))

        delivered[:] = []  # Clear without reassigning
        self.chan1.basic_publish('topic', 'routing.key.one.foo.two', 'blah')
        self.assertEqual([('q1', 'topic', 'routing.key.one.foo.two', 'blah'),
                          ('q3', 'topic', 'routing.key.one.foo.two', 'blah'),
                          ], sorted(delivered))

    def test_basic_get(self):
        self.set_up_broker()
        self.assertEqual('get-empty', self.chan1.basic_get('q1').method.name)
        self.q1.put('foo', 'rkey.foo', mkmsg('blah'))
        self.assertEqual('blah', self.chan1.basic_get('q1').content.body)
        self.assertEqual('get-empty', self.chan1.basic_get('q1').method.name)

    def test_consumer_wrangling(self):
        self.set_up_broker()
        self.chan1.queue_bind('q1', 'direct', 'foo')
        self.assertEqual(set(), self.q1.consumers)
        self.chan1.basic_consume('q1', 'tag1')
        self.assertEqual(set(['tag1']), self.q1.consumers)
        self.chan1.basic_consume('q1', 'tag2')
        self.assertEqual(set(['tag1', 'tag2']), self.q1.consumers)
        self.chan1.basic_cancel('tag2')
        self.assertEqual(set(['tag1']), self.q1.consumers)
        self.chan1.basic_cancel('tag2')
        self.assertEqual(set(['tag1']), self.q1.consumers)

    @inlineCallbacks
    def test_fake_amqclient(self):
        spec = get_spec(make_vumi_path_abs("config/amqp-spec-0-8.xml"))
        amq_client = fake_amqp.FakeAMQClient(spec, {}, self.broker)
        d = Deferred()

        class TestWorker(Worker):
            @inlineCallbacks
            def startWorker(self):
                self.pub = yield self.publish_to('test.pub')
                self.conpub = yield self.publish_to('test.con')
                self.con = yield self.consume('test.con', self.consume_msg)

            def consume_msg(self, msg):
                # NOTE: One-shot.
                d.callback(msg)

        worker = TestWorker(amq_client, {})
        yield worker.startWorker()
        yield worker.pub.publish_json({'message': 'foo'})
        yield worker.conpub.publish_json({'message': 'bar'})
        msg = yield d
        self.assertEqual({'message': 'bar'}, msg.payload)

    # This is a test which actually connects to the AMQP broker.
    #
    # It originally existed purely as a mechanism for discovering what
    # the real client/broker's behaviour is in order to duplicate it
    # in the fake one. I've left it in here for now in case we need to
    # do further investigation later, but we *really* don't want to
    # run it as part of the test suite.
    #
    # @inlineCallbacks
    # def test_zzz_real_amqclient(self):
    #     print ""
    #     from vumi.service import WorkerCreator
    #     options = {
    #         "hostname": "127.0.0.1",
    #         "port": 5672,
    #         "username": "vumi",
    #         "password": "vumi",
    #         "vhost": "/develop",
    #         "specfile": "config/amqp-spec-0-8.xml",
    #         }
    #     wc = WorkerCreator(options)
    #     d = Deferred()

    #     class TestWorker(Worker):
    #         @inlineCallbacks
    #         def startWorker(self):
    #             self.pub = yield self.publish_to('test.pub')
    #             self.pub.routing_key_is_bound = lambda _: True
    #             self.conpub = yield self.publish_to('test.con')
    #             self.con = yield self.consume('test.con', self.consume_msg)
    #             d.callback(None)

    #         def consume_msg(self, msg):
    #             print "CONSUMED!", msg
    #             return True

    #     factory = wc.create_worker_by_class(TestWorker, {})
    #     yield d
    #     worker = factory.worker
    #     yield worker.pub.publish_json({"foo": "bar"})
    #     yield worker.conpub.publish_json({"bar": "baz"})
    #     yield worker.pub.channel.queue_declare(queue='test.foo')
    #     yield worker.pub.channel.queue_bind(queue='test.foo',
    #                                         exchange='vumi',
    #                                         routing_key='test.pub')
    #     yield worker.pub.publish_json({"foo": "bar"})
    #     print "getting..."
    #     foo = yield worker.pub.channel.basic_get(queue='test.foo')
    #     print "got:", foo
    #     yield worker.stopWorker()
