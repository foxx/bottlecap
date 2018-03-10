import code
import click
import json
import inspect
import bottle

from six.moves.urllib.parse import urljoin
from bottle import Bottle, request, HTTPError, HTTPResponse
from decimal import Decimal
from helpful import ensure_subclass, extend_instance
from bottlecap import exceptions as ex
from blinker import signal

from bottlecap.negotiation import ContentNegotiationPlugin
from bottlecap.views import View

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
# BottleCap application
############################################################

class BottleCap(Bottle):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signal_exception = signal('exception')

        # disable all existing plugins
        self.plugins = []
        
        # install content negotiation plugin
        cnp = ContentNegotiationPlugin()
        self.install(cnp)

        # we must always disable autojson
        #app.config['json.disable'] = True
        #app.config['json.enable'] = False
        #app.config['autojson'] = False

    def apply(self, callback, context):
        def wrapper(*args, **kwargs):
            # XXX: for some reason, we cannot use extend_instance on request :X
            request.base_url = RequestMixin.base_url
            request.get_full_url = RequestMixin.get_full_url

            # process request
            return callback(*args, **kwargs)
        return wrapper

    #def handle_exception(self, exc):
    #    """
    #    BottleCap becomes the default handler for all exceptions and
    #    never passes them upstream, effectively eliminating catchall
    #    functionality
    #    """
    #    # All exceptions are passed to subscribers for processing
    #    self.signal_exception.send(exc)
        # All other exceptions should be converted into HTTPError
        #if request.app.catchall is True:
        #    nexc = ex.ServerError()
        #    raise HTTPError(nexc.status_code, nexc.to_dict())

    def route(self, *args, **kwargs):
        # treat cbv routing differently
        cls = args[0] if len(args) else None
        if inspect.isclass(cls) and issubclass(cls, View):
            return self.routecbv(cls)
        
        # fallback to standard routing
        return super().route(*args, **kwargs)

    def routecbv(self, view):
        """
        Same as route(), but for CBVs (class based views)

        :attr view: View class
        """
        ensure_subclass(view, View)

        # views must provide at least path and method
        if not view._meta.path:
            raise RuntimeError('CBV does not specify `path` in meta')
        if not view._meta.method:
            raise RuntimeError('CBV does not specify `method` in meta')

        kwargs = {}
        kwargs['path'] = view._meta.path
        kwargs['method'] = view._meta.method
        kwargs['name'] = view._meta.name
        kwargs['skip'] = view._meta.skip
        kwargs['apply'] = view._meta.plugins
        kwargs['meta'] = view._meta

        cb = view.as_callable()
        self.route(**kwargs)(cb)
        return view

    #def default_error_handler(self, exc):
    #    """
    #    Errors should always use content negotiation from view by default,
    #    otherwise fallback onto the application defaults
    #    """
    #    raise exc



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


