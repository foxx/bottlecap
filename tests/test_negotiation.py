import bottle
import webtest
import json
import pytest

from pytest import raises_regexp
from copy import copy
from bottle import HTTPResponse, HTTPError, request
from helpful import ClassDict

from bottlecap import View
from bottlecap.negotiation import *
from bottlecap.mediatype import *

class ExampleRenderer(Renderer):
    media_types = 'vnd/example'


class EchoView(ContentNegotiationViewMixin):
    path = '/echo'
    method = ['GET', 'POST']

    def dispatch(self):
        return 'hello'


class JSONEchoView(EchoView):
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]

    def dispatch(self):
        return HTTPResponse([1,2,3])


class ExampleErrorView(ContentNegotiationViewMixin):
    path = '/error'
    method = ['GET', 'POST']

    def dispatch(self):
        raise HTTPError('418 Teapot', [1,2,3])


class TestDefaultContentNegotiation(object):
    def test_guess_content_type(self):
        cneg = DefaultContentNegotiation()
        a = cneg.guess_content_type("hello")
        b = MediaType('application/octet-stream')
        assert a == b

        a = cneg.guess_content_type(None)
        assert a == None

    def test_select_renderer(self):
        cneg = DefaultContentNegotiation()
        renderer, content_type = \
            cneg.select_renderer('application/json', [JSONRenderer])
        assert renderer == JSONRenderer
        assert content_type == 'application/json'

    def test_select_parser(self):
        cneg = DefaultContentNegotiation()
        parser = cneg.select_parser('application/json', [JSONParser])
        assert parser == JSONParser

        parser = cneg.select_parser('application/json', [])
        assert parser == None


class TestContentNegotiationViewMixin(object):
    def test_form_parser(self, app):
        """Attempt to parse form data"""
        @app.routecbv
        class ExampleView(EchoView):
            parser_classes = [FormParser]

        payload = {'a': 'b'}
        resp = app.webtest.post('/echo', params=payload)
        assert resp.status_code == 200
        assert resp.body == b'hello'
        assert request.negotiation_context.parser == FormParser
        assert request.body_parsed == payload


    @pytest.mark.parametrize("view_render_errors", [True, False])
    def test_json_parser_invalid_body(self, app, view_render_errors):
        """Attempt to parse invalid JSON payload"""

        @app.routecbv
        class ExampleView(JSONEchoView):
            render_errors = view_render_errors

        resp = app.webtest.post('/echo',
            params="{001010101",
            headers={'Content-Type': 'application/json'},
            expect_errors=True)

        if view_render_errors:
            assert resp.status == '400 Invalid Body'
            assert resp.body == b''
            assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        else:
            assert resp.status == '400 Invalid Body'
            assert b'DOCTYPE HTML PUBLIC' in resp.body
            assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'

    def test_json_parser(self, app):
        """Attempt to parse body with JSON"""

        @app.routecbv
        class ExampleView(JSONEchoView):
            parser_classes = [JSONParser]

        payload = {'a': 'b'}
        resp = app.webtest.post_json('/echo', params=payload)

    def test_json_renderer(self, app):
        """Ensure JSON renderer is working"""
        app.routecbv(JSONEchoView)
        resp = app.webtest.get('/echo')
        assert resp.status == '200 OK'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert resp.body == b'[1, 2, 3]'

    def test_renderer_selection(self, app):
        """Ensure media type fallbacks work correctly"""
        class MultiRenderer(Renderer):
            media_types = ['vnd/example', 'vnd/hello']

        @app.routecbv
        class TestView(EchoView):
            renderer_classes = [MultiRenderer]
            mismatch_renderer_class = MultiRenderer

        resp = app.webtest.get('/echo')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'vnd/example'

        resp = app.webtest.get('/echo',
            headers={'Accept': 'vnd/example'})
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'vnd/example'

        resp = app.webtest.get('/echo',
            headers={'Accept': 'vnd/hello'})
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'vnd/hello'

        MultiRenderer.default_media_type = 'vnd/hello'
        resp = app.webtest.get('/echo', headers={'Accept': 'vnd/wtf'})
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'vnd/hello'


    @pytest.mark.parametrize("view_render_errors", [True, False])
    def test_dispatch_error(self, app, view_render_errors):
        """Dispatch raises an HTTPError"""

        @app.routecbv
        class ExampleView(ExampleErrorView):
            render_errors = view_render_errors
            renderer_classes = [JSONRenderer]

        resp = app.webtest.get('/error',
            expect_errors=True)

        if view_render_errors:
            assert resp.status == '418 Teapot'
            assert resp.body == b'[1, 2, 3]'
            assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        else:
            assert resp.status == '418 Teapot'
            assert b'DOCTYPE HTML PUBLIC' in resp.body
            assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'

    def test_guess_content_type(self, app):
        """Content type header is missing on request"""

        @app.routecbv
        class ExampleView(JSONEchoView):
            parser_classes = [OctetStreamParser]

        resp = app.webtest.post('/echo',
            params="wtf", headers={'Content-Type': ''})

        assert resp.status == '200 OK'
        assert resp.body == b'[1, 2, 3]'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'

        assert request.body_parsed == b'wtf'
        assert request.negotiation_context.parser == OctetStreamParser

    @pytest.mark.parametrize("view_render_errors", [True, False])
    def test_invalid_content_type(self, app, view_render_errors):
        """Content type header is invalid on request"""

        @app.routecbv
        class ExampleView(JSONEchoView):
            render_errors = view_render_errors

        resp = app.webtest.post('/echo', 
            params="wtf",
            headers={'Content-Type': 'invalid'},
            expect_errors=True)

        if view_render_errors:
            assert resp.status == '400 Invalid Content Type'
            assert resp.body == b''
            assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        else:
            assert resp.status == '400 Invalid Content Type'
            assert b'DOCTYPE HTML PUBLIC' in resp.body
            assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'

    @pytest.mark.parametrize("view_render_errors", [True, False])
    def test_invalid_accept_header(self, app, view_render_errors):
        """Accept header is invalid on request"""

        @app.routecbv
        class ExampleView(JSONEchoView):
            render_errors = view_render_errors

        resp = app.webtest.get('/echo', 
            headers={'Accept': 'invalid'},
            expect_errors=True)

        assert resp.status == '400 Invalid Accept'
        assert b'DOCTYPE HTML PUBLIC' in resp.body
        assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'

    def test_missing_accept_header(self, app):
        """Accept header missing on request"""
        app.routecbv(JSONEchoView)
        resp = app.webtest.get('/echo')
        assert resp.status == '200 OK'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert resp.body == b'[1, 2, 3]'

    def test_mismatch_accept_header_true(self, app):
        """
        Accept header does not match any renderers, however
        a mismatch renderer has been provided
        """
        @app.routecbv
        class ExampleView(JSONEchoView):
            mismatch_renderer_class = ExampleRenderer

            def dispatch(self):
                return HTTPResponse("wtf")

        resp = app.webtest.get('/echo', 
            headers={'Accept': 'vnd/invalid'})
        assert resp.status == '200 OK'
        assert resp.headers['Content-Type'] == 'vnd/example'
        assert resp.body == b'wtf'
        assert request.negotiation_context.renderer == ExampleRenderer

    @pytest.mark.parametrize("view_render_errors", [True, False])
    def test_mismatch_accept_header_false(self, app, view_render_errors):
        """
        Accept header does not match any renderers, and no
        mismatch renderer has been provided
        """
        @app.routecbv
        class ExampleView(JSONEchoView):
            mismatch_renderer_class = None
            render_errors = view_render_errors

        resp = app.webtest.get('/echo', 
            headers={'Accept': 'vnd/invalid'},
            expect_errors=True)
        assert resp.status == '406 Not Acceptable'
        assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert b'DOCTYPE HTML PUBLIC' in resp.body
        assert request.negotiation_context.renderer == None

    def test_plain_text_renderer(self, app):
        """Ensure plain text is rendered correctly
        """
        @app.routecbv
        class ExampleView(EchoView):
            renderer_classes = [PlainTextRenderer]

            def dispatch(self):
                return HTTPResponse('hello')

        resp = app.webtest.get('/echo')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/plain; charset=UTF-8'
        assert resp.body == b'hello'
        assert request.negotiation_context.renderer == PlainTextRenderer

    def test_html_renderer(self, app):
        """Ensure html is rendered correctly
        """
        @app.routecbv
        class ExampleView(EchoView):
            renderer_classes = [HTMLRenderer]

            def dispatch(self):
                return HTTPResponse('hello')

        resp = app.webtest.get('/echo')
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/html; charset=UTF-8'
        assert resp.body == b'hello'
        assert request.negotiation_context.renderer == HTMLRenderer


'''
    def test_html_renderer(self, app):
        cneg = ContentNegotiation(renderers=HTMLRenderer())
        view = get_echo_view(cneg)
        app.routecv(view)

        resp = app.webtest.get('/echo')
        assert resp.status_code == 200
        assert resp.body == b'hello'
        assert isinstance(request.cneg.renderer, HTMLRenderer)
'''

