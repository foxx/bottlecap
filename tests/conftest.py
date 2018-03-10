import pytest
import bottle

from webtest import TestApp
from bottle import Bottle
from bottlecap import BottleCap
from bottlecap.views import View
from bottlecap.negotiation import ContentNegotiationPlugin

class HelloView(View):
    class Meta:
        path = '/hello'
        method = ['GET']

    def dispatch(self):
        return 'world'


@pytest.fixture
def app(request):
    app = Bottle(catchall=False)
    app.webtest = TestApp(app)

    bc = BottleCap()
    app.install(bc)

    app.route(HelloView)
   
    return app
