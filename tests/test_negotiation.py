import pytest

from bottle import request
from bottlecap.negotiation import *
from bottlecap.mediatype import *
from bottlecap.views import View

class ExampleRenderer(Renderer):
    media_types = 'vnd/example'


class EchoView(View):
    class Meta:
        path = '/echo'
        method = ['GET', 'POST']

    def dispatch(self):
        return 'hello'

class JSONEchoView(View):
    class Meta:
        path = '/echo'
        method = ['GET', 'POST']
        parser_classes = [JSONParser]
        renderer_classes = [JSONRenderer]

    def dispatch(self):
        return [1,2,3]


class ErrorView(View):
    class Meta:
        path = '/error'
        method = ['GET', 'POST']

    def dispatch(self):
        raise HTTPError('418 Teapot', 'some error')


class JSONErrorView(View):
    path = '/error'
    method = ['GET', 'POST']

    def dispatch(self):
        raise HTTPError('418 Teapot', [1,2,3])



class TestContentNegotiation:
    def test_guess_content_type(self):
        cneg = ContentNegotiation()
        a = cneg.guess_content_type("hello")
        b = MediaType('application/octet-stream')
        assert a == b

        a = cneg.guess_content_type(None)
        assert a == None

    def test_select_renderer_valid(self):
        cneg = ContentNegotiation(renderer_classes=[JSONRenderer])
        renderer, content_type = cneg.select_renderer('application/json')
        assert renderer == JSONRenderer
        assert content_type == 'application/json'

    def test_select_renderer_blank(self):
        cneg = ContentNegotiation()
        renderer, content_type = cneg.select_renderer('application/json')
        assert renderer == None
        assert content_type == None

    def test_select_parser_valid(self):
        cneg = ContentNegotiation(parser_classes=[JSONParser])
        parser = cneg.select_parser('application/json')
        assert parser == JSONParser

    def test_select_parser_blank(self):
        cneg = ContentNegotiation()
        parser = cneg.select_parser('application/json')
        assert parser == None


###########################################################
# Test cases for content negotiation parsers
###########################################################

class TestContentNegotiationParsers:

    def test_form_parser(self, app):
        """Attempt to parse form data"""

        @app.route
        class ExampleView(EchoView):
            class Meta:
                parser_classes = [FormParser]

        payload = {'a': 'b'}
        resp = app.webtest.post('/echo', params=payload)
        assert resp.status_code == 200
        assert resp.body == b'hello'
        assert request.nctx.parser == FormParser
        assert request.body_parsed == payload

    def test_json_parser_invalid_body(self, app):
        """Attempt to parse invalid JSON payload"""

        app.route(JSONEchoView)
        resp = app.webtest.post('/echo',
            params="{001010101",
            headers={'Content-Type': 'application/json'},
            expect_errors=True)

        assert resp.status == '400 Invalid Body'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert resp.json == {
            'error_code': 'bad_request', 
            'error_desc': 'There was an error parsing the request body', 
            'error_detail': 'Expecting property name enclosed in double quotes:' \
                            ' line 1 column 2 (char 1)', 
            'status_code': '400 Invalid Body'}


