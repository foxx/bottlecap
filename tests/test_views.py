import pytest
from bottlecap.negotiation import *
from bottlecap.mediatype import *
from bottlecap.views import View


#############################################################
# Test views
#############################################################

class TestContentNegotiationViewMixin(object):
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


    def test_dispatch_error(self, app):
        """Dispatch raises an HTTPError"""

        @app.routecbv
        class ExampleView(ExampleErrorView):
            renderer_classes = [JSONRenderer]

        resp = app.webtest.get('/error', expect_errors=True)

        assert resp.status == '418 Teapot'
        assert resp.body == b'[1, 2, 3]'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'

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

    def test_invalid_content_type(self, app):
        """Content type header is invalid on request"""

        app.routecbv(JSONEchoView)
        resp = app.webtest.post('/echo', 
            params="wtf",
            headers={'Content-Type': 'invalid'},
            expect_errors=True)

        assert resp.status == '400 Invalid Content Type'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert resp.json == {
            'error_code': 'bad_request', 
            'error_desc': "The request header 'Content-Type' was malformed", 
            'error_detail': None, 
            'status_code': '400 Invalid Content Type'}

    def test_invalid_accept_header(self, app):
        """Accept header is invalid on request"""

        app.routecbv(JSONEchoView)
        resp = app.webtest.get('/echo', 
            headers={'Accept': 'invalid'},
            expect_errors=True)

        assert resp.status == '400 Invalid Accept'
        assert resp.headers['Content-Type'] == 'application/json; charset=UTF-8'
        assert resp.json == {
            'error_code': 'bad_request', 
            'error_desc': "The request header 'Accept' was malformed", 
            'error_detail': None, 
            'status_code': '400 Invalid Accept'}

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

