import pytest
from webtest import TestApp

from bottlecap import BottleCap

@pytest.fixture
def app(request):
    app = BottleCap(catchall=False)
    app.webtest = TestApp(app)
    return app
