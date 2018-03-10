from box import Box

class BaseView(type):
    @property
    def _meta(cls):
        o = {}
        for scls in reversed(cls.__mro__):
            meta = getattr(scls, 'Meta', None)
            if not meta: continue
            fields = dict([ (f, getattr(meta, f)) for f in dir(scls.Meta) 
                       if not f.startswith('_') ])
            o.update(fields)
        assert False, o
        return 123

class View(metaclass=BaseView):
    pass

class ObjectA(View):
    class Meta:
        a = 'b'


class ObjectB(ObjectA):
    class Meta:
        hello = 'world'


assert False, ObjectB._meta
