from six import with_metaclass
from json import JSONDecoder, JSONEncoder
from bottle import HTTPResponse, HTTPError, request
from bottlecap import View
from helpful import (ClassDict, NoneType, makelist, 
    iter_ensure_instance, ensure_instance, flatteniter, 
    get_exception)

from .mediatype import *

__all__ = ['ContentNegotiationContext', 'Renderer', 'PlainTextRenderer', 
           'HTMLRenderer', 'JSONRenderer', 'Parser', 'JSONParser', 'FormParser', 
           'DefaultContentNegotiation', 'OctetStreamParser',
           'ContentNegotiationViewMixin']

# XXX: Charset handling appears to be broken, needs fix

############################################################
# Renderers
############################################################

class BaseRenderer(type):
    def __new__(cls, name, bases, attrs):
        obj = super(BaseRenderer, cls).__new__(cls, name, bases, attrs)
        obj.media_types = cast_media_type_list(obj.media_types)
        if not obj.default_media_type:
            obj.default_media_type = obj.media_types[0] \
                if obj.media_types else None
        return obj


class Renderer(with_metaclass(BaseRenderer)):
    media_types = None
    default_media_type = None
    charset = None

    @classmethod
    def render(self, body): # pragma: nocover
        """
        :attr body: Response body
        :type body: bytes
        """
        return body


class PlainTextRenderer(Renderer):
    media_types = 'text/plain'
    charset = 'utf-8'

    @classmethod
    def render(self, body):
        return body.encode(self.charset)


class HTMLRenderer(Renderer):
    media_types = 'text/html'
    charset = 'utf-8'

    @classmethod
    def render(self, body):
        return body.encode(self.charset) if body else None


class JSONRenderer(Renderer):
    media_types = 'application/json'
    encoder = JSONEncoder
    charset = 'utf-8'

    @classmethod
    def render(self, body):
        if body is None:
            return None
        return self.encoder().encode(body).encode(self.charset)


############################################################
# Parsers
############################################################

class BaseParser(type):
    def __new__(cls, name, bases, attrs):
        obj = super(BaseParser, cls).__new__(cls, name, bases, attrs)
        obj.media_types = cast_media_type_list(obj.media_types)
        return obj


class Parser(with_metaclass(BaseParser)):
    media_types = None

    @classmethod
    def parse(self, body): # pragma: nocover
        """
        :attr body: Request body
        :type body: bytes
        """
        return body


class OctetStreamParser(Parser):
    media_types = 'application/octet-stream'
    charset = 'utf-8'

    @classmethod
    def parse(self, body):
        return body


class JSONParser(Parser):
    media_types = 'application/json'
    decoder = JSONDecoder
    charset = 'utf-8'

    @classmethod
    def parse(self, body):
        return self.decoder().decode(body.decode(self.charset)) \
            if body else None


class FormParser(Parser):
    media_types = [
        MediaType('application/x-www-form-urlencoded'), 
        MediaType('multipart/form-data')]

    @classmethod
    def parse(self, body):
        return request.forms


############################################################
# Base objects
############################################################

class ContentNegotiationContext(ClassDict):
    """
    Injected into `bottle.request` on every request which
    has content negotiation enabled
    """
    def __init__(self):
        super(ContentNegotiationContext, self).__init__()
        self.parser = None
        self.renderer = None
        self.request_content_type = None
        self.request_accept = None
        self.response_content_type = None
        self.negotiation = None


class DefaultContentNegotiation(object):
    def guess_content_type(self, body):
        """
        As per RFC7231 section 3.1.1.5, attempt to guess content type
        if one hasn't been provided, and use fallback assumption
        of application/octet-stream.

        https://tools.ietf.org/html/rfc7231#section-3.1.1.5

        :returns: MediaType instance
        """
        if body:
            return MediaType('application/octet-stream')

    def select_parser(self, media_type, parsers):
        """
        Determine which parser should be used for request

        :attr media_type: Media type to match
        :attr parsers: list of parser classes
        :returns: ContentParser instance
        """
        for parser in parsers:
            matched = parser.media_types.first_match(media_type)
            if matched: return parser
        return None

    def select_renderer(self, media_type, renderers):
        """
        Determine which renderer should be used for response

        :attr media_type: Media type to match
        :attr renderers: list of renderer classes
        :returns: (renderer, media_type)
        """
        for renderer in renderers:
            matched = renderer.media_types.first_match(media_type)
            if matched: 
                return renderer, matched[1]
        return None, None


class ContentNegotiationViewMixin(View):
    # Content negotiation class to use
    content_negotiation_class = DefaultContentNegotiation

    # Choose from these parsers, if no matching content type
    # can be found then return "415 Unsupported Media Type"
    parser_classes = None

    # Choose from these renderers, if no matching content type
    # can be found then return the first by default
    # See http://tools.ietf.org/html/rfc7231#section-5.3.2
    renderer_classes = None

    # If client provides an Accept header which is not present in
    # our list of renderers, then use this one by default. Otherwise
    # return "406 Not Acceptable"
    # See http://tools.ietf.org/html/rfc7231#section-5.3.2
    mismatch_renderer_class = None

    # Error responses should be rendered, instead of being handled
    # by the application error handlers. If no renderer can be determined
    # then fallback to the app error handlers
    render_errors = True

    def __call__(self):
        request.negotiation_context = cneg = ContentNegotiationContext()
        request.negotiator = self.content_negotiation_class()
        request.body_parsed = None

        try:
            response = super(ContentNegotiationViewMixin, self).__call__()
        except HTTPResponse:
            if not self.render_errors:
                raise
            if self.render_errors:
                if not cneg.renderer:
                    raise
                response = HTTPResponse()
                get_exception().apply(response)

        if cneg.renderer:
            if not isinstance(response, HTTPResponse):
                response = HTTPResponse(response)
            response.body = cneg.renderer.render(response.body)
            response.content_type = cneg.response_content_type
        return response

    def pre_dispatch(self):
        super(ContentNegotiationViewMixin, self).pre_dispatch()
        body = request._get_body_string()
        cneg = request.negotiation_context

        # determine which content types are accepted by the client
        try:
            raw_accept = request.headers.get('Accept', '*/*')
            cneg.request_accept = MediaTypeList(raw_accept)
        except ParseError as e:
            raise HTTPError('400 Invalid Accept', 
                exception=get_exception())

        # find appropriate renderer
        if cneg.request_accept:
            cneg.renderer, cneg.response_content_type = \
                request.negotiator.select_renderer(
                    media_type=cneg.request_accept,
                    renderers=self.renderer_classes or [])

            if not cneg.renderer:
                if self.renderer_classes:
                    if not self.mismatch_renderer_class:
                        raise HTTPError('406 Not Acceptable')
                    cneg.renderer = self.mismatch_renderer_class
                    cneg.response_content_type = \
                        self.mismatch_renderer_class.default_media_type

        # determine what content type is sent by the request
        try:
            raw_content_type = request.headers.get('Content-Type', None)
            if raw_content_type:
                cneg.request_content_type = MediaType(raw_content_type)
        except ParseError:
            raise HTTPError(
                status='400 Invalid Content Type',
                exception=get_exception())

        # attempt to guess content type if necessary
        if body and not raw_content_type:
            cneg.request_content_type = \
                request.negotiator.guess_content_type(body)

        # find appropriate content parser
        if cneg.request_content_type:
            cneg.parser = request.negotiator.select_parser(
                media_type=cneg.request_content_type,
                parsers=self.parser_classes or [])
            if not cneg.parser:
                raise HTTPError('415 Unsupported Media Type')

        # process body
        if cneg.parser:
            try:
                request.body_parsed = cneg.parser.parse(body)
            except:
                raise HTTPError("400 Invalid Body", 
                    exception=get_exception())
