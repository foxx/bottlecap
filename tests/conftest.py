import pytest

from webtest import TestApp
from bottle import Bottle
from bottlecap import BottleCap

def hello():
    return 'world'


@pytest.fixture
def app(request):
    app = Bottle(catchall=False)
    app.route('/hello', ['GET'], hello)
    app.webtest = TestApp(app)

    bc = BottleCap()
    app.install(bc)

    return app
