import uuid

from twisted.internet.defer import inlineCallbacks
from twisted.python import log
from twisted.web import http
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from vumi.transports.base import Transport


class HttpRpcHealthResource(Resource):
    isLeaf = True

    def __init__(self, transport):
        self.transport = transport
        Resource.__init__(self)

    def render_GET(self, request):
        request.setResponseCode(http.OK)
        return "pReq:%s" % len(self.transport.requests)


class HttpRpcResource(Resource):
    isLeaf = True

    def __init__(self, transport):
        self.transport = transport
        Resource.__init__(self)

    def render_(self, request, http_action=None):
        log.msg("HttpRpcResource HTTP Action: %s" % (request,))
        request.setHeader("content-type", "text/plain")
        uu = str(uuid.uuid4().get_hex())
        self.transport.requests[uu] = request
        self.transport.handle_raw_inbound_message(uu, request)
        return NOT_DONE_YET

    def render_GET(self, request):
        return self.render_(request, "render_GET")

    def render_POST(self, request):
        return self.render_(request, "render_POST")


class HttpRpcTransport(Transport):
    """Base class for synchronous HTTP transports.

    Because a reply from an application worker is needed before the HTTP
    response can be completed, a reply needs to be returned to the same
    transport worker that generated the inbound message. This means that
    currently there many only be one transport worker for each instance
    of this transport of a given name.
    """

    @inlineCallbacks
    def setup_transport(self):
        self.requests = {}

        # start receipt web resource
        self.web_resource = yield self.start_web_resources(
            [
                (HttpRpcResource(self), self.config['web_path']),
                (HttpRpcHealthResource(self), 'health'),
            ],
            self.config['web_port'])

    @inlineCallbacks
    def teardown_transport(self):
        yield self.web_resource.loseConnection()

    def handle_outbound_message(self, message):
        log.msg("HttpRpcTransport consuming %s" % (message))
        if message.payload.get('in_reply_to') and 'content' in message.payload:
            self.finishRequest(
                    message.payload['in_reply_to'],
                    message.payload['content'])

    def handle_raw_inbound_message(self, msgid, request):
        raise NotImplementedError("Sub-classes should implement"
                                  " handle_raw_inbound_message.")

    def finishRequest(self, uuid, message=''):
        data = str(message)
        log.msg("HttpRpcTransport.finishRequest with data:", repr(data))
        log.msg(repr(self.requests))
        request = self.requests.get(uuid)
        if request:
            request.write(data)
            request.finish()
            del self.requests[uuid]
