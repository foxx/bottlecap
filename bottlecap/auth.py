"""
Authentication library for BottleCap
"""

import logging
import jwt

from bottle import request
from bottlecap import View
from typing import Union, List
from box import Box
from uuid import UUID

from bottlecap import exceptions as ex

logger = logging.getLogger(__name__)

##############################################################
# JWT Auth Plugin
##############################################################

class User:
    def __init__(self, guid:UUID, roles:List[str], is_active:bool, options:dict=None):
        self._data = dict(guid=guid, roles=roles, is_active=is_active, options=options)

    @property
    def guid(self):
        return self._data['guid']

    @property
    def is_active(self):
        return self._data['is_active']

    @property
    def options(self):
        return Box(self._data['options'] or {})

    @property
    def roles(self):
        """Return roles as lowered set"""
        return set([ r.lower() for r in self._data['roles']])
    
    def has_role(self, role:str):
        """Check user assumes a particular role.

        :param role: role to check for
        :type role:  str

        :return: result of a check
        :rtype:  bool
        """
        return role in self.roles

    def has_roles(self, *roles:str):
        """Check user assumes multiple roles in the same time.

        :param roles: roles to check for
        :type roles:  list of str

        :return: result of a check
        :rtype:  bool
        """
        return all(self.has_role(role) for role in roles)

    def has_any_role(self, *roles:str):
        """Check user assumes at least one role from a list.

        :param roles: roles that can be assumed
        :type roles:  list of str

        :return result of a check
        :rtype: bool
        """
        return any(self.has_role(role) for role in roles)


##############################################################
# JWT Auth Plugin
##############################################################


class JWTAuthPlugin:
    """Extends for JWT authentication support
    """

    # XXX: needs type hints
    def __init__(self, public_key, private_key=None, valsig=True, 
                 algos=['RS512'], user_model_cls=User):
        """
        XXX: needs docs
        """
        self.jwt_public_key = public_key
        self.jwt_private_key = private_key
        self.jwt_valsig = valsig
        self.jwt_algos = algos
        self.user_model_cls = user_model_cls

    def get_token_from_request(self):
        """Returns raw token from request headers"""

        # ensure auth token is provided
        if 'Authorization' not in request.headers:
            return

        auth = request.headers['Authorization']
        if not auth.startswith('Bearer:'):
            raise ex.BadRequestError(error_desc='Invalid authorization header')

        # extract auth token
        token = auth.split(':', 1)[1].strip()
        if not token:
            raise ex.BadRequestError(error_desc='Invalid authorization header')

        # we require a public key to proceed
        if self.jwt_public_key is None:
            raise RuntimeError("Stone: JWT Public Key not configured")

    def get_user_from_token(self, token):
        """Lookup user for request"""

        ttoken = Box(token)

        # convert to a user object
        try:
            guid = UUID(token.user.guid)
        except:
            raise RuntimeError('Malformed JWT')

        assert isinstance(ttoken.user.roles, list)
        assert isinstance(ttoken.user.is_active, bool)

        user = User(guid=guid,
                    roles=set(ttoken.user.roles), 
                    is_active=ttoken.user.is_active)

        # check whether user has been disabled
        if request.user.is_active is False:
            raise NotAuthorizedError(error_desc='User has been disabled')

    def token_decode(self, token):
        """Wrapper method for decoding JWTs"""
        return jwt.decode(token, self.jwt_public_key, algorithms=self.jwt_algos)

    def token_encode(self, data):
        """Wrapper method for encoding JWTs"""
        return jwt.encode(data, self.jwt_private_key, algorithm=self.jwt_algos[0])

    def apply(self, callback, context):

        def wrapper(*args, **kwargs):
            # assign defaults
            request.user = None
            request.jwt = None

            # extract raw token from request
            raw_token = self.get_token_from_request()
            if raw_token is None: return
            token = self.token_decode(raw_token)
            if token is None: return
            request.jwt = token

            # lookup user from token
            request.user = self.get_user_from_token(token)

            # continue with request
            return callback(*args, **kwargs)

        return wrapper
        

class AuthenticationViewMixin:
    """Provides authentication support to Bottle CBVs
    """
    user_required = True
    roles_required = None
    roles_accepted = None

    def pre_dispatch(self):
        # do we require a user to be present?
        if self.user_required and not isinstance(request.user, User):
            raise NotAuthenticatedError()

        # user must have ALL these roles
        if self.roles_required:
            has_roles = request.user.has_roles(*self.roles_required)
            if not has_roles:
                raise NotAuthorizedError()

        # user must have at least one of these roles
        if self.roles_accepted:
            has_roles = request.user.has_any_roles(*self.roles_accepted)
            if not has_roles:
                raise NotAuthorizedError()

        super().pre_dispatch()


