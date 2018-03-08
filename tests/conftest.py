import pytest

from webtest import TestApp
from bottle import Bottle
from bottlecap import BottleCapPlugin

@pytest.fixture
def app(request):
    app = Bottle(catchall=False)
    app.webtest = TestApp(app)

    bcp = BottleCapPlugin()
    app.install(bcp)

    return app
