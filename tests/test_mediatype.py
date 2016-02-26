import pytest

from copy import copy
from random import Random
from decimal import Decimal
from bottlecap.negotiation import *
from bottlecap.mediatype import *

random = Random()
random.seed(0)

class TestMediaType(object):
    def test_hash(self):
        dict().get(MediaType('text/html'))

    def test_parse_benchmark(self, benchmark):
        func = lambda: MediaType('text/html;hello=3;level=1;alpha=2;q=1')
        benchmark(func)

    def test_rich_comparisons(self):
        mt = MediaType
        assert mt('text/html') == mt('text/html')
        assert mt('text/xml') != mt('text/html')

        assert not mt('text/html') > mt('text/html')
        assert not mt('text/html') < mt('text/html')
        assert mt('text/html') >= mt('text/html')
        assert mt('text/html') <= mt('text/html')

        assert mt('text/html') == 'text/html'
        assert mt('text/html') != 'text/xml'
        assert 'text/html' == mt('text/html')
        assert 'text/html' != mt('text/xml')

    def test_str(self):
        """
        Output string should always match input, including parameter ordering
        """
        values = [
            'text/html',
            'text/html+json',
            'text/html;level=1',
            'text/html;level=1;q=0.1',
            'text/html;level=1;q=1',
            'text/html;q=1;level=1',
            'text/html;q=1;level=1;alpha=2',
            'text/html;level=1;q=1;alpha=2',
            'text/html;level=1;alpha=2;hello=3;q=1',
            'text/html;hello=3;level=1;alpha=2;q=1']

        for value in values:
            a = MediaType(value)
            assert str(a) == value

    def test_parse(self):
        """
        Ensure different media types are parsed correctly
        """
        def check_exact_match(result, type, subtype, parameters, suffix=None):
            assert result.type == type
            assert result.subtype == subtype
            assert result.suffix == suffix
            assert dict(result.parameters) == parameters

            q = result.parameters.get('q', None)
            if q is not None:
                assert result.quality == Decimal(q)

        a = MediaType('text/*;q=0.3')
        b = dict(type='text', subtype='*', parameters={'q':'0.3'})
        check_exact_match(a, **b)

        a = MediaType('text/html;q=0.7')
        b = dict(type='text', subtype='html', parameters={'q':'0.7'})
        check_exact_match(a, **b)

        a = MediaType('text/html;level=1')
        b = dict(type='text', subtype='html', parameters={'level':1})
        check_exact_match(a, **b)

        a = MediaType('text/html;level=2;q=0.4')
        b = dict(type='text', subtype='html', parameters={'q': '0.4', 'level': 2})
        check_exact_match(a, **b)

        a = MediaType('*/*;q=0.5')
        b = dict(type='*', subtype='*', parameters={'q': '0.5'})
        check_exact_match(a, **b)

        a = MediaType('vnd/example.v2+json;level=1')
        b = dict(type='vnd', subtype='example.v2+json', parameters={'level':1},
            suffix='json')
        check_exact_match(a, **b)

        with pytest.raises(ParseError):
            MediaType('*/text;q=1')
        with pytest.raises(ParseError):
            MediaType('text;q=1')
        with pytest.raises(ParseError):
            MediaType('text/html;q')

    def test_compare(self):
        def comp(a, b, **kwargs):
            a = MediaType(a)
            b = MediaType(b)
            return a.compare(b, **kwargs)

        assert comp('text/html', 'text/html') == 0
        assert comp('text/html', 'text/xml') == 0

        assert comp('text/html', 'text/*') == 1
        assert comp('text/*', 'text/html') == -1

        assert comp('text/html', '*/*') == 1
        assert comp('*/*', 'text/html') == -1

        # with parameters
        assert comp('text/html;level=1', 'text/html') == 1
        assert comp('text/html', 'text/html;level=1') == -1

        # with quality
        assert comp('text/html;q=1', 'text/html;q=0.7') == 1
        assert comp('text/html;q=0.7', 'text/html;q=1') == -1

        # with parameters and quality
        assert comp('text/html;level=2', 'text/html;level=3;q=0.4') == 1

        # without parameters
        assert comp('text/html;level=1', 'text/html',
            ignore_parameters=True) == 0
        assert comp('text/html', 'text/html;level=1',
            ignore_parameters=True) == 0

        # without quality
        assert comp('text/html;q=1', 'text/html;q=0.7',
            ignore_quality=True) == 0
        assert comp('text/html;q=0.7', 'text/html;q=1',
            ignore_quality=True) == 0

    def test_is_match(self):
        def comp(a, b, **kwargs):
            a = MediaType(a)
            b = MediaType(b)
            return a.is_match(b, **kwargs)

        # type handling
        assert comp("*/*", "text/html") is True
        assert comp("other/html", "text/html") is False

        # subtype handling
        assert comp("text/html", "text/xhtml") is False
        assert comp("text/html", "text/html") is True
        assert comp("text/html", "text/*") is True
        assert comp("text/*", "text/html") is True
        assert comp("text/*", "text/*") is True

        # parameters handling (without ignore)
        assert comp("text/html", "text/html;level=1") is False
        assert comp("text/html;level=1", "text/html") is False
        assert comp("text/html;level=1", "text/html;level=2") is False
        assert comp("text/html;level=2", "text/html;level=1") is False
        assert comp("text/html;level=1", "text/html;level=1") is True

        # quality handling (without ignore)
        assert comp("text/html;q=0.9", "text/html") is True
        assert comp("text/html;q=0.9", "text/html;q=0.7") is False
        assert comp("text/html;q=0.9", "text/html;q=1") is True
        assert comp("text/html;q=0.9", "text/html") is True
        assert comp("text/html", "text/html;q=0.9") is False

        # parameters and quality handling (without ignore)
        assert comp('text/html;level=2', 'text/html;level=3;q=0.4') is False

        # quality/weights handling (with ignore)
        assert comp("text/html;q=0.9", "text/html;q=0.7",
            ignore_quality=True) is True
        assert comp("text/html;q=0.9", "text/html;q=1",
            ignore_quality=True) is True
        assert comp("text/html;q=0.9", "text/html",
            ignore_quality=True) is True
        assert comp("text/html", "text/html;q=0.9",
            ignore_quality=True) is True

        # parameters handling (with ignore)
        assert comp("text/html", "text/html;level=1", 
            ignore_parameters=True) is True
        assert comp("text/html;level=1", "text/html", 
            ignore_parameters=True) is True
        assert comp("text/html;level=1", "text/html;level=2", 
            ignore_parameters=True) is True
        assert comp("text/html;level=2", "text/html;level=1", 
            ignore_parameters=True) is True
        assert comp("text/html;level=1", "text/html;level=1", 
            ignore_parameters=True) is True


class TestMediaTypeList(object):
    def test_setitem(self):
        result = MediaTypeList([])
        result.append(MediaType('text/html'))

    def test_parse_best_match(self, benchmark):
        a = self.parse_media_types([
            'text/html;level=2', 'text/html;level=1', 'text/html;level=3;q=0.4', 
            'text/html;q=0.7', 'text/*;q=0.3', '*/*;q=0.5'])
        b = self.parse_media_types([
            'text/html;level=2', 'text/html;level=1', 'text/html;level=3;q=0.4', 
            'text/html;q=0.7', 'text/xml;q=0.3', 'application/json;q=0.5'])

        func = lambda: a.best_match(b)
        benchmark(func)

    def parse_media_types(self, values):
        result = MediaTypeList([ MediaType(x) for x in values ])
        assert len(result) == len(values)
        return result

    def test_best_match(self):
        def check_best_match(a, b, c):
            result = a.best_match(b)
            got = [ [str(x1), str(x2)] for x1, x2 in result ]
            assert got == c

        # single items
        a = self.parse_media_types(['text/html'])
        b = self.parse_media_types(['text/html'])
        c = [ ['text/html', 'text/html'] ]
        check_best_match(a, b, c)

        # multiple items
        a = self.parse_media_types(['text/html', 'text/xml', 'application/json;q=5'])
        b = self.parse_media_types(['text/html'])
        c = [ ['text/html', 'text/html'] ]
        check_best_match(a, b, c)

        # complex items
        a = self.parse_media_types([
            'text/html;level=2',
            'text/html;level=1',
            'text/html;level=3;q=0.4',
            'text/html;q=0.7', 
            'text/*;q=0.3',
            '*/*;q=0.5'])

        b = self.parse_media_types([
            'text/html;level=2',
            'text/html;level=1',
            'text/html;level=3;q=0.4', 
            'text/html;q=0.7', 
            'text/xml;q=0.3',
            'application/json;q=0.5'])

        c = [['text/html;level=2', 'text/html;level=2'], 
             ['text/html;level=1', 'text/html;level=1'], 
             ['text/html;level=3;q=0.4', 'text/html;level=3;q=0.4'], 
             ['text/html;q=0.7', 'text/html;q=0.7'], 
             ['text/xml;q=0.3', 'text/*;q=0.3'], 
             ['application/json;q=0.5', '*/*;q=0.5']]
        check_best_match(a, b, c)

        # XXX: test without quality
        # XXX: test without parameters
        # XXX: test without quality and parameters

    def test_best_match_precedence(self):
        a = self.parse_media_types([
            'text/html;level=2',
            'text/html;level=1',
            'text/html;level=3',
            'text/xml;level=3;q=0.4', 
            'text/html;q=0.7', 
            'text/*;q=0.3',
            '*/*;q=0.5'])

        b = self.parse_media_types([
            'text/html;level=2',
            'text/html;level=1',
            'text/html;level=3',
            'text/xml;level=3;q=0.4', 
            'text/html;q=0.7', 
            'text/xml;q=0.3',
            'application/json;q=0.5'])

        # test precedence
        for i in range(100):
            expected = [ str(x) for x in b 
                if str(x).startswith('text/html')]
            got = [ str(x[0]) for x in a.best_match(b) 
                if str(x[0]).startswith('text/html') ]
            random.shuffle(b)

        # XXX: test without quality?
        # XXX: test without parameters?
        # XXX: test without quality and parameters?
    
    def test_precedence(self):
        values = [
            'text/xml;q=3',
            'text/html;level=5',
            'application/json;q=4',
            'text/html;level=2',
            'text/html;level=3',
            'text/html;level=1',
            'audio/mp4',
            'text/html;level=4']

        def only_text_html(values):
            return [ str(x) for x in values if str(x).startswith('text/html') ]

        for i in range(100):
            random.shuffle(values)
            result = self.parse_media_types(values).sorted_by_precedence()
            a = only_text_html(result)
            b = only_text_html(values)
            assert a == b
