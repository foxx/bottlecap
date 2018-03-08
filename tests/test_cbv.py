import pytest
import bottle
import webtest

from copy import copy
from bottle import Bottle, HTTPResponse
from bottlecap import View

lol = '''
class HelloView(View):
    class Meta:
        path = '/hello'
        method = ['GET']
        name = 'hello'

    def dispatch(self):
        return HTTPResponse('hello')


class TestBottleCapCBV(object):
    @py.test.fixture
    def app(self, request):
        app = BottleCap()
        app.routecv(HelloView)
        app.webtest = webtest.TestApp(app)
        return app

    def test_routecv(self, app):
        resp = app.webtest.get('/hello')
        assert resp.body == b'hello'

    def test_get_full_url(self, app):
        resp = app.webtest.get('/hello')
        url = bottle.request.get_full_url('hello')
        assert url == 'http://localhost/hello'

    def test_base_url(self, app):
        app.webtest.get('/hello')
        assert bottle.request.base_url == 'http://localhost'

        app.webtest.get('/hello', extra_environ={
            'HTTP_X_FORWARDED_PROTO': 'https',
            'HTTP_HOST': 'example.com:443'})
        assert bottle.request.base_url == 'https://example.com'

        app.webtest.get('/hello', extra_environ={
            'HTTP_X_FORWARDED_PROTO': 'https',
            'HTTP_HOST': 'example.com:8081'})
        assert bottle.request.base_url == 'https://example.com:8081'

        app.webtest.get('/hello', extra_environ={
            'HTTP_HOST': 'example.com:8080'})
        assert bottle.request.base_url == 'http://example.com:8080'


def test_view_meta():

    class A(View):
        class Meta:
            path = '/a'
            name = 'example'
            method = ['GET']
    
    class B(A):
        class Meta:
            path = '/b'
            method = ['POST']

    class C(B):
        class Meta:
            path = '/c'
            method = ['PUT']

    a_cls_meta = A._meta
    a_inst_meta = A()._meta

    b_cls_meta = B._meta
    b_inst_meta = B()._meta

    c_cls_meta = C._meta
    c_inst_meta = C()._meta

    assert a_cls_meta.path == '/a'
    assert a_inst_meta.path == '/a'
    assert b_cls_meta.path == '/b'
    assert b_inst_meta.path == '/b'
    assert c_cls_meta.path == '/c'
    assert c_inst_meta.path == '/c'

    assert a_cls_meta.name == 'example'
    assert a_inst_meta.name == 'example'
    assert b_cls_meta.name == 'example'
    assert b_inst_meta.name == 'example'
    assert c_cls_meta.name == 'example'
    assert c_inst_meta.name == 'example'

    a_cls_meta.test2 = 'example'
    assert a_cls_meta.test2 == 'example'
    assert a_inst_meta.test2 == 'example'
    assert 'test2' not in b_cls_meta
    assert 'test2' not in b_inst_meta
    assert 'test2' not in c_cls_meta
    assert 'test2' not in c_inst_meta

    c_cls_meta.test3 = 'example'
    assert c_cls_meta.test3 == 'example'
    assert c_inst_meta.test3 == 'example'
    assert 'test3' not in a_cls_meta
    assert 'test3' not in a_inst_meta
    assert 'test3' not in b_cls_meta
    assert 'test3' not in b_inst_meta
    


'''
