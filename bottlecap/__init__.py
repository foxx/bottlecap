import code
import click

from six.moves.urllib.parse import urljoin
from bottle import Bottle, request
from decimal import Decimal
from helpful import ensure_subclass, extend_instance


############################################################
# Bottle Cap mixin
############################################################

class RequestMixin(object):
    @property
    def base_url(self):
        """
        Return base URL constructed from current request
        """
        url = "{}://{}".format(
            request.urlparts.scheme,
            request.urlparts.hostname)
        port = request.urlparts.port
        # XXX: needs test
        if port and port not in (80, 443):
            url += ":{}".format(port)
        return url

    def get_full_url(self, routename, **kwargs):
        """
        Construct full URL using components from current
        bottle request, merged with get_url()

        For example:
        https://example.com/hello?world=1

        XXX: Needs UT
        """
        url = self.app.get_url(routename, **kwargs)
        return urljoin(self.base_url, url)


############################################################
# CBVs (class based views)
############################################################

class View:
    name = None
    method = None
    path = None
    skip = None
    plugins = None
    config = None

    def __init__(self, **url_args):
        self.url_args = url_args
        self.request = request

    def __call__(self):
        self.pre_dispatch()
        return self.dispatch()

    def dispatch(self): # pragma: nocover
        # XXX: should replace with ABCs
        raise NotImplementedError("Subclass must implement dispatch")

    @classmethod
    def as_callable(cls):
        def inner(**url_args):
            return cls(**url_args)()
        return inner

    def pre_dispatch(self):
        pass


############################################################
# Management CLI
############################################################

@click.group()
def cli(): # pragma: no cover
    pass

@cli.command(name='runserver', help='Start development server')
@click.option('--host', '-h',
    default='127.0.0.1', type=str,
    help='Server hostname/IP')
@click.option('--port', '-p',
    default='8080', type=int,
    help='Server port')
@click.option('--use-reloader',
    type=bool, flag_value=True, default=True,
    help='should the server automatically restart the python '
         'process if modules were changed?')
@click.option('--use-debugger',
    type=bool, flag_value=True, default=True,
    help='should the werkzeug debugging system be used?')
@click.option('--use-evalex',
    type=bool, flag_value=True, default=True,
    help='should the exception evaluation feature be enabled?')
@click.option('--extra-files',
    type=click.Path(), default=None, 
    help='a list of files the reloader should watch additionally '
         'to the modules. For example configuration files.')
@click.option('--static',
    type=click.Path(), default=None, multiple=True,
    help='path to serve static files from via SharedDataMiddleware')
@click.option('--reloader-type',
    type=click.Choice(['stat', 'watchdog']), default=None, 
    help='the type of reloader to use. The default is auto detection.')
@click.option('--reloader-interval',
    type=Decimal, default=0.5, 
    help='the interval for the reloader in seconds')
@click.option('--passthrough-errors',
    type=bool, flag_value=True, default=True,
    help='set this to True to disable the error catching. '
         'This means that the server will die on errors but '
         'it can be useful to hook debuggers in (pdb etc.)')
@click.option('--threaded',
    type=bool, flag_value=True, default=False,
    help='should the process handle each request in a separate thread?')
@click.option('--processes',
    type=int, default=1, 
    help='if greater than 1 then handle each request in a new process up '
         'to this maximum number of concurrent processes.')
def cli_runserver(**kwargs): # pragma: no cover
    kwargs['application'] = None
    return run_simple(**kwargs)


@cli.command(name='ishell', help='Start IPython shell')
def cli_ishell(ctx): # pragma: no cover
    from IPython import start_ipython
    start_ipython(argv=[])


@cli.command(name='shell', help='Start python shell')
def cli_shell(ctx): # pragma: no cover
    code.interact(local=locals())


############################################################
# BottleCap application
############################################################

class BottleCapMixin:
    """Mixin applied to bottle application upon installation
    """

    def routecbv(self, view):
        """
        Same as route(), but for CBVs (class based views)

        :attr view: View class
        """
        ensure_subclass(view, View)

        kwargs = {}
        kwargs['path'] = view.path
        kwargs['method'] = view.method
        kwargs['name'] = view.name
        kwargs['skip'] = view.skip
        kwargs['config'] = view.config
        kwargs['apply'] = view.plugins

        assert view.path, \
            "View meta must provide a valid `path`"
        assert view.method, \
            "View meta must provide a valid `method`"

        self.route(**kwargs)(view.as_callable())
        return view


class BottleCapPlugin:
    def __init__(self):
        super().__init__()

    def setup(self, app):
        # ensure this plugin isn't already installed
        for other in app.plugins:
            # XXX: needs test
            if isinstance(other, BottleCapPlugin):
                raise PluginError('Bottlecap already installed on app')

        # add necessary hooks
        app.add_hook('before_request', self.hook_before_request)

        # extend app
        extend_instance(app, BottleCapMixin)

    def hook_before_request(self):
        """Executed before every request"""
        # XXX: for some reason, we cannot use extend_instance on request :X
        request.base_url = RequestMixin.base_url
        request.get_full_url = RequestMixin.get_full_url

    def apply(self, callback, context):
        return callback

