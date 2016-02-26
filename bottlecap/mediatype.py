from decimal import Decimal
from helpful import ensure_instance, padded_split, makelist
from collections import OrderedDict
from copy import copy

__all__ = ['ParseError', 'MediaType', 'MediaTypeList', 'cast_media_type', 
           'cast_media_type_list']


class ParseError(Exception):
    """Unable to parse media type"""


def cast_media_type(value):
    """
    Convert str/bytes to MediaType, or return if value
    is already an instance of MediaType

    >>> cast_media_type('text/html')
    MediaType('text/html')
    >>> m = MediaType('text/html')
    >>> cast_media_type(m)
    MediaType('text/html')
    """
    ensure_instance(value, (str, bytes, MediaType))
    if isinstance(value, (str, bytes)):
        return MediaType(value)
    elif isinstance(value, MediaType):
        return value


def cast_media_type_list(values):
    """
    >>> cast_media_type_list(MediaTypeList(['text/html']))
    [MediaType('text/html')]
    >>> cast_media_type_list('text/html')
    [MediaType('text/html')]
    >>> cast_media_type_list(None)
    []
    """
    if isinstance(values, MediaTypeList):
        return values
    elif values:
        return MediaTypeList(values)
    else:
        return MediaTypeList()

class MediaType(dict):
    """
    Represents media type as an inspectable object with
    support for rich comparisons
    """
    def __repr__(self):
        return "MediaType('{}')".format(str(self))

    def __str__(self):
        """
        Returns media type as string representation
        e.g. text/html;q=0.4
        """
        value = "{}/{}".format(self.type, self.subtype)
        if self.parameters:
            value += ";"
            parameters = ';'.join([ 
                '{0!s}={1!s}'.format(*x) for x in self.parameters.items() ])
            value += parameters
        return value

    def __init__(self, value):
        """
        Represents parsed media type

        >>> MediaType('text/html')
        MediaType('text/html')
        >>> MediaType(dict(type='text', subtype='html'))
        MediaType('text/html')
        >>> MediaType(dict(type='text', subtype='html', parameters={'q': 1}))
        MediaType('text/html;q=1')
        """
        super(MediaType, self).__init__()

        if isinstance(value, (str, bytes)):
            value = self._parse(value)
        ensure_instance(value, dict)

        def load(type, subtype, parameters=None):
            self['type'] = type
            self['subtype'] = subtype

            if parameters is not None:
                ensure_instance(parameters, dict)
                quality = parameters.get('q', None)
                if quality is not None:
                    ensure_instance(quality, (str, bytes, int, float, Decimal))
                self['parameters'] = parameters
            else:
                self['parameters'] = {}

        load(**value)

    type = property(lambda self: self['type'])
    subtype = property(lambda self: self['subtype'])
    parameters = property(lambda self: self['parameters'])
    suffix = property(lambda self: padded_split(self.subtype, "+", 1)[1])

    @property
    def format(self):
        """
        Attempt to match content type to common handler

        :attr media_type: e.g. text/html
        :type media_type: str or instance of MediaType
        :rtype: str or None

        >>> MediaType('application/xml').format
        'xml'
        >>> MediaType('application/json').format
        'json'
        >>> MediaType('vnd/special+json').format
        'json'
        >>> MediaType('text/html').format
        'html'
        >>> MediaType('text/plain').format
        'plain'
        >>> MediaType('wtf/world').format
        """
        full_type = "{}/{}".format(self.type, self.subtype)
        if full_type == 'application/json' or self.suffix == 'json':
            return 'json'
        elif full_type == 'application/xml' or self.suffix == 'xml':
            return 'xml'
        elif full_type == 'text/html':
            return 'html'
        elif full_type == 'text/plain':
            return 'plain'
        return None

    @property
    def suffix(self):
        # Allow suffix via "plus sign", see RFC3023
        subtype, suffix = padded_split(self.subtype, "+", 1)
        return suffix


    @property
    def quality(self):
        q = self.parameters.get('q', 1)
        return Decimal(q)

    @classmethod
    def _parse(self, value):
        """
        Parse media type string into components
        :attr value: Media type value 
                 e.g. text/html;level=2;q=0.4
        :type value: str, bytes
        :returns: MediaType instance
        """
        full_type, parameters = padded_split(value.strip(), ';', 1)
        full_type = '*/*' if full_type == '*' else full_type

        type, subtype = padded_split(full_type, '/', 1)
        if type is None or subtype is None:
            raise ParseError()

        # type can only be a wildcard with subtype
        if type == '*' and subtype != '*':
            raise ParseError()

        def fix_param(x):
            key, value = padded_split(x, '=', 1)
            if not key or not value:
                raise ParseError()
            if str.isdigit(value):
                value = int(value)
            return (key, value)

        parameters = OrderedDict([ fix_param(param) 
            for param in parameters.split(";") ]) if parameters else {}

        kwargs = dict(type=type, subtype=subtype, parameters=parameters)
        return kwargs

    def compare(self, other, ignore_quality=False, ignore_parameters=False):
        """
        Compare media types and determine ordering preference as
        defined by RFC7231.

        :type a: instance of MediaType
        :type b: instance of MediaType
        :type ignore_quality: bool
        :type ignore_parameters: bool
        :returns: int (-1, 0 or 1)
        """
        a = self
        b = other
        ensure_instance(a, MediaType)
        ensure_instance(b, MediaType)

        if a.type == '*' and b.type != '*':
            return -1
        elif a.type != '*' and b.type == '*':
            return 1
        elif a.subtype == '*' and b.subtype != '*':
            return -1
        elif a.subtype != '*' and b.subtype == '*':
            return 1

        if not ignore_parameters:
            a_len = len([ key for key in a.parameters.keys() if key != 'q' ])
            b_len = len([ key for key in b.parameters.keys() if key != 'q' ])
            if a_len < b_len:
                return -1
            elif a_len > b_len:
                return 1

        if not ignore_quality:
            if a.quality < b.quality:
                return -1
            elif a.quality > b.quality:
                return 1

        return 0

    def is_match(self, other, ignore_quality=False, ignore_parameters=False):
        """
        Compare media types and determine if they are an equal match

        For quality comparison, if A has a quality of 0.7 then B must
        have a quality of 0.7 or above to match.

        XXX: Should this return the matched media type, rather than bool?

        :type other: instance of MediaType
        :type ignore_quality: bool
        :type ignore_parameters: bool
        :returns: bool
        """

        a = self
        b = other

        # ensure type matches
        if a.type != '*' and b.type != '*' and a.type != b.type:
           return False

        # ensure subtype matches
        if (a.subtype != '*' and b.subtype != '*' 
            and a.subtype != b.subtype):
            return False

        # as specified by RFC7231, treat quality as a weight
        # q=0 means "not acceptable"
        if (not ignore_quality and 
            (a.quality == 0 or b.quality == 0 or a.quality > b.quality)):
            return False

        # ensure parameters match, where applicable
        if not ignore_parameters:
            a_dict = a.parameters.copy()
            a_dict.pop('q', None)
            b_dict = b.parameters.copy()
            b_dict.pop('q', None)
            if a_dict != b_dict:
                return False

        return True

    def __lt__(self, other):
        return self.compare(other) == -1

    def __gt__(self, other):
        return self.compare(other) == 1

    def __ge__(self, other):
        return self.compare( other) in (0, 1)

    def __le__(self, other):
        return self.compare(other) in (-1, 0)

    def __eq__(self, other):
        if isinstance(other, (str, bytes)):
            return str(self) == other
        return super(MediaType, self).__eq__(other)

    def __hash__(self):
        return hash(str(self))


class MediaTypeList(list):
    def __init__(self, items=None, *args, **kwargs):
        """
        Represent list of media types

        >>> MediaTypeList('html/text,html/xml')
        [MediaType('html/text'), MediaType('html/xml')]
        >>> MediaTypeList(['html/text', 'html/xml'])
        [MediaType('html/text'), MediaType('html/xml')]
        >>> MediaTypeList([MediaType('html/text'), \
            MediaType('html/xml')])
        [MediaType('html/text'), MediaType('html/xml')]
        >>> MediaTypeList()
        []
        """
        if isinstance(items, (str, bytes)):
            items = items.split(",")
        items = makelist(items)
        items = [ cast_media_type(item) for item in items ] if items else []
        super(MediaTypeList, self).__init__(items, *args, **kwargs)

    def __setitem__(self, key, value):
        ensure_instance(value, MediaType)
        super(MediaTypeList, self).__setitem__(key, value)

    def sorted_by_precedence(self):
        """Sort media types by precedence as defined in RFC2616"""
        # XXX: needs without_quality/without_parameters
        return sorted(self, reverse=True)

    def is_match(self, media_type, ignore_quality=False, ignore_parameters=False):
        """
        Check if media type is supported in this list
        :attr media_type: instance of MediaType

        >>> a = MediaTypeList(['text/html', 'text/xml'])
        >>> a.is_match(MediaType('text/html'))
        True
        >>> a.is_match(MediaType('text/plain'))
        False
        >>> a.is_match('text/html')
        True
        >>> a.is_match('text/plain')
        False
        """
        for a in self.sorted_by_precedence():
            if a.is_match(cast_media_type(media_type), 
                ignore_quality=ignore_quality,
                ignore_parameters=ignore_parameters):
                return True
        return False

    def first_match(self, other, **kwargs):
        """
        Shorthand for best_match()[0]
        XXX: Needs doctest
        """
        result = self.best_match(other, **kwargs)
        return result[0] if result else None

    def best_match(self, other, ignore_quality=False, ignore_parameters=False):
        """
        Return media types based on best match as defined in RFC7231
        https://tools.ietf.org/html/rfc7231#section-5.3.1
        https://tools.ietf.org/html/rfc7231#section-5.3.2

        Preference order is based on "closest match", however RFC
        states that parameter matching is optional, and parameter
        matching can be disabled by using `ignore_parameters`.

        It may be desirable to ignore quality weighting, which can
        be done using `ignore_quality`

        Returns list of (media_type, matched_media_type)

        :attr other: instance of MediaTypeList
        """
        other = cast_media_type_list(other)
        ensure_instance(other, MediaTypeList)

        kwargs = dict(
            ignore_quality=ignore_quality, 
            ignore_parameters=ignore_parameters)
        matched = []
        remaining = copy(other)
        for a in self.sorted_by_precedence():
            if not len(remaining):
                break
            compared = [ ( b, a.is_match(b, **kwargs)) for b in remaining ]
            matched += [ (media_type, a) for media_type, match 
                in compared if match ]
            remaining = [ media_type for media_type, match 
                in compared if not match ]
        return matched

