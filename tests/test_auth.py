import pytest
import jwt

from uuid import uuid4
from bottle import request
from bottlecap.auth import User, JWTAuthPlugin


@pytest.fixture
def jwt_pub_priv_key():
    """
    Generate random pub/priv key for JWT
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    key = rsa.generate_private_key(
        backend=default_backend(), 
        public_exponent=65537,
        key_size=2048)

    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo)

    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption())

    return (public_key, pem)


@pytest.fixture
def dummyuser():
    roles = ['r1', 'r2', 'r3']
    options = dict(hello='world')
    user = User(guid=uuid4(), roles=roles, is_active=True, options=options)
    return user


class TestUser:
    def test_is_active(self, dummyuser):
        assert dummyuser.is_active is True
        with pytest.raises(AttributeError):
            dummyuser.is_active = False

    def test_options(self, dummyuser):
        assert dummyuser.options == dict(hello='world')
        assert dummyuser.options.hello == 'world'
        with pytest.raises(AttributeError):
            dummyuser.options = {}

        dummyuser.options.hello = 'wtf'
        assert dummyuser.options.hello == 'world'

    def test_roles(self, dummyuser):
        assert dummyuser.roles == set(['r1', 'r2', 'r3'])
        with pytest.raises(AttributeError):
            dummyuser.roles = []

    def test_has_role(self, dummyuser):
        assert dummyuser.has_role('r1') is True
        assert dummyuser.has_role('no') is False

    def test_has_roles(self, dummyuser):
        assert dummyuser.has_roles('r1') is True
        assert dummyuser.has_roles('r1', 'r2') is True
        assert dummyuser.has_roles('r1', 'no') is False

    def test_has_any_role(self, dummyuser):
        assert dummyuser.has_any_role('r1') is True
        assert dummyuser.has_any_role('r1', 'r2') is True
        assert dummyuser.has_any_role('r1', 'no') is True
        assert dummyuser.has_any_role('no') is False


class TestJWTAuthPlugin:

    def create_plugin(self):
        pub, priv = jwt_pub_priv_key()
        return JWTAuthPlugin(public_key=pub, private_key=priv, valsig=True)

    def test_jwt_encode_decode(self):
        jap = self.create_plugin()

        data = dict(hello='world')
        token = jap.token_encode(data)
        
        data_decoded = jap.token_decode(token)
        assert data == data_decoded

    def test_request_token(self, app):
        # install plugin
        jap = self.create_plugin()
        app.install(jap)

        # if no auth header provided, then don't expect a token
        resp = app.webtest.get('/hello')
        assert resp.status_code == 200
        assert request.user is None
        assert request.jwt is None

        # invalid auth header should raise error
        headers = {'Authorization': 'invalid'}
        resp = app.webtest.get('/hello', headers=headers, expect_errors=True)
        assert resp.status_code == 400
        assert resp.json == {'error_code': 'bad_request', 
                             'error_desc': 'Invalid authorization header', 
                             'status_code': 400}



