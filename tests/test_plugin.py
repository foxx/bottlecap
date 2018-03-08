import pytest

from bottle import request
from bottlecap import View

class ExampleView(View):
    name = 'test'
    path = '/test'
    method = 'GET'

    def dispatch(self):
        return 'yay'


def test_base_url(app):
    app.routecbv(ExampleView)
    resp = app.webtest.get('/test')
    assert request.base_url == 'http://localhost'
    assert request.get_full_url('test') == 'http://localhost/test'

