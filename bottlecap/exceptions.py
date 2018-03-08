"""Exception classes of this library"""

class BaseError(Exception):
    """Base exception class
    """

    def __init__(self, status_code:int=None, error_code:str=None, error_desc:str=None, 
                 errors=None, original_exc:Exception=None):
        super().__init__(self)

        if status_code is not None: 
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        if error_desc is not None:
            self.error_desc = error_desc

        self.errors = errors
        self.original_exc = original_exc

    def to_dict(self):
        o = dict(error_code=self.error_code,
                 error_desc=self.error_desc,
                 status_code=self.status_code)
        if self.errors: o['errors'] = self.errors
        return o


class ServerError(BaseError):
    """Base exception for all server errors"""
    status_code = 500
    error_code = "server_error"
    error_desc = "There was a server error, please try again later"


class ClientError(BaseError):
    """Base exception for all client errors"""


class BadRequestError(ClientError):
    status_code = 400
    error_code = "bad_request"
    error_desc = "Request was not properly formed"


class RequestSchemaError(ClientError):
    """Request schema was invalid"""
    status_code = 400
    error_code = "bad_request"
    error_desc = "Request payload does not match schema"

    
class ResponseSchemaError(ServerError):
    """Response schema was invalid"""


class NotAuthenticatedError(ClientError):
    """Request was invalid"""
    status_code = 401
    error_code = "auth_error"
    error_desc = "Client authentication failed"


class NotAuthorizedError(ClientError):
    """Request was invalid"""
    status_code = 403
    error_code = "auth_error"
    error_desc = "Client has insufficient authorization"

