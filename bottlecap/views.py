from bottlecap.negotiation import ContentNegotiation
from helpful import ClassDict

############################################################
# CBVs (class based views)
############################################################

class ViewMeta(type):
    """Adds support for class meta"""

    @property
    def _meta(cls):
        o = {}
        for scls in reversed(cls.__mro__):
            meta = getattr(scls, 'Meta', None)
            if not meta: continue
            fields = dict([ (f, getattr(meta, f)) for f in dir(scls.Meta) 
                       if not f.startswith('_') ])
            o.update(fields)
        return ClassDict(o)


class BaseView(metaclass=ViewMeta):
    class Meta:
        name = None
        method = None
        path = None
        skip = None
        plugins = None
        config = None

    def __init__(self, **url_args):
        self.url_args = url_args

    def __call__(self):
        return self.dispatch()

    def dispatch(self): # pragma: nocover
        # XXX: should replace with ABCs
        raise NotImplementedError("Subclass must implement dispatch")

    @classmethod
    def as_callable(cls):
        def inner(**url_args):
            return cls(**url_args)()
        return inner


class ContentNegotiationViewMixin:

    class Meta:
        # Content negotiation class to use
        content_negotiation_class = ContentNegotiation

        # Choose from these parsers, if no matching content type
        # can be found then return "415 Unsupported Media Type"
        parser_classes = None

        # Choose from these renderers, if no matching content type
        # can be found then return the first by default
        # See http://tools.ietf.org/html/rfc7231#section-5.3.2
        renderer_classes = None

        # If client provides an Accept header which is not present in
        # our list of renderers, then use this one by default. Otherwise
        # return "406 Not Acceptable"
        # See http://tools.ietf.org/html/rfc7231#section-5.3.2
        mismatch_renderer_class = None


class View(BaseView, ContentNegotiationViewMixin):
    pass
