import pytest

from estnltk import Text
from estnltk import Layer
from estnltk import Span
from estnltk import AmbiguousSpan
from estnltk.layer.annotation import Annotation
from estnltk.layer import AmbiguousAttributeTupleList
from estnltk.layer import AmbiguousAttributeList
from estnltk.layer import AttributeTupleList
from estnltk.layer import AttributeList


def test_add_span():
    text = Text('0123456789')
    layer = Layer(name='ambiguous', attributes=['a', 'b', 'c'], ambiguous=True)
    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a='s1', b=True, c=None))
    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a='s2', b=False, c=5))
    layer.add_span(Span(start=0, end=2, legal_attributes=layer.attributes, a='s3', b=True, c=None))
    text['ambiguous'] = layer

    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a='s1', b=True, c=None))
    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a='s4', b=False, c=5))

    assert len(layer.span_list) == 3
    assert isinstance(layer[0], AmbiguousSpan)
    assert isinstance(layer[1], AmbiguousSpan)
    assert isinstance(layer[2], AmbiguousSpan)
    assert len(layer[0]) == 1
    assert len(layer[1]) == 1
    assert len(layer[2]) == 2

    layer = Layer(name='ambiguous', attributes=['a', 'b', 'c'], ambiguous=False)
    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a='s1', b=True, c=None))
    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a='s2', b=False, c=5))
    layer.add_span(Span(start=0, end=2, legal_attributes=layer.attributes, a='s3', b=True, c=None))

    with pytest.raises(ValueError):
        layer.add_span(Span(start = 0, end = 1, legal_attributes = layer.attributes, a = 's1', b = True,  c = None))
    with pytest.raises(ValueError):
        layer.add_span(Span(start = 1, end = 2, legal_attributes = layer.attributes, a = 's4', b = False, c = 5))

    assert len(layer.span_list) == 3
    assert isinstance(layer[0], Span)
    assert isinstance(layer[1], Span)
    assert isinstance(layer[2], Span)


def test_layer_indexing():
    t = Text("0123456789")
    layer = Layer(name='base',
                  attributes=['a', 'b', 'c'],
                  default_values={'a': 'default a', 'b': 'default b', 'c': 'default c'},
                  ambiguous=False)

    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a=1,    b=11,   c=21))
    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a=2,    b=12))
    layer.add_span(Span(start=2, end=3, legal_attributes=layer.attributes, a=3))
    layer.add_span(Span(start=3, end=4, legal_attributes=layer.attributes))
    layer.add_span(Span(start=4, end=5, legal_attributes=layer.attributes, a=5,    b=15,   c=25))
    layer.add_span(Span(start=5, end=6, legal_attributes=layer.attributes, a=6,    b=16,   c=None))
    layer.add_span(Span(start=6, end=7, legal_attributes=layer.attributes, a=7,    b=None, c=None ))
    layer.add_span(Span(start=7, end=8, legal_attributes=layer.attributes, a=None, b=None, c=None))
    t['base'] = layer

    span_2 = layer[2]
    assert isinstance(span_2, Span)
    assert span_2.text == '2'
    assert span_2.a == 3
    assert span_2.b == 'default b'
    assert span_2.c == 'default c'

    assert isinstance(layer['a'], AttributeList)
    assert isinstance(layer.a, AttributeList)
    assert layer['a'] == layer.a
    assert isinstance(layer['b'], AttributeList)
    assert isinstance(layer.b, AttributeList)
    assert layer['b'] == layer.b
    assert isinstance(layer['c'], AttributeList)
    assert isinstance(layer.c, AttributeList)
    assert layer['c'] == layer.c

    assert len(layer['a']) == 8
    assert len(layer['b']) == 8
    assert len(layer['c']) == 8

    assert isinstance(layer['a','b'], AttributeTupleList)
    assert isinstance(layer[['a','b']], AttributeTupleList)
    assert layer['a','b'] == layer[['a', 'b']]
    assert layer['a','b'] == layer[('a', 'b')]
    assert len(layer[['a','b']]) == 8
    assert isinstance(layer[['a']], AttributeTupleList)
    assert layer['a'] != layer[['a']]
    assert len(layer[['a']]) == 8

    atl = t.base['a', 'b']
    del t.base
    assert atl == AttributeTupleList([[1, 11],
                                      [2, 12],
                                      [3, 'default b'],
                                      ['default a', 'default b'],
                                      [5, 15],
                                      [6, 16],
                                      [7, None],
                                      [None, None]],
                                     ('a', 'b'))


def test_ambiguous_layer_indexing():
    t = Text("0123456789")
    layer = Layer(name='base',
                  attributes=['a', 'b', 'c'],
                  default_values={'a': 'default a', 'b': 'default b'},
                  ambiguous=True)
    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a=1, b=11, c=21))
    layer.add_span(Span(start=0, end=1, legal_attributes=layer.attributes, a=1, b=11, c=21))

    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a=2, b=12))
    layer.add_span(Span(start=1, end=2, legal_attributes=layer.attributes, a=2, b=123))

    layer.add_span(Span(start=2, end=3, legal_attributes=layer.attributes, a=3))

    layer.add_span(Span(start=3, end=4, legal_attributes=layer.attributes))
    layer.add_span(Span(start=3, end=4, legal_attributes=layer.attributes, a=4, b=None))

    layer.add_span(Span(start=4, end=5, legal_attributes=layer.attributes, a=5, b=15, c=25))
    layer.add_span(Span(start=5, end=6, legal_attributes=layer.attributes, a=6, b=16, c=None))
    layer.add_span(Span(start=6, end=7, legal_attributes=layer.attributes, a=7, b=None, c=None))
    layer.add_span(Span(start=7, end=8, legal_attributes=layer.attributes, a=None, b=None, c=None))
    layer.add_span(Span(start=7, end=8, legal_attributes=layer.attributes, a=None, b=None, c=None))
    t['base'] = layer

    span_3 = layer[3]
    assert isinstance(span_3, AmbiguousSpan)
    assert len(span_3) == 2
    assert isinstance(span_3[0], Annotation)
    assert span_3[0].text == '3'
    assert span_3[0].a == 'default a'
    assert span_3[0].b == 'default b'
    assert span_3[0].c is None
    assert span_3[1].text == '3'
    assert span_3[1].a == 4
    assert span_3[1].b is None
    assert span_3[1].c is None

    assert isinstance(layer['a'], AmbiguousAttributeList)
    assert isinstance(layer.a, AmbiguousAttributeList)
    assert layer['a'] == layer.a
    assert isinstance(layer['b'], AmbiguousAttributeList)
    assert isinstance(layer.b, AmbiguousAttributeList)
    assert layer['b'] == layer.b
    assert isinstance(layer['c'], AmbiguousAttributeList)
    assert isinstance(layer.c, AmbiguousAttributeList)
    assert layer['c'] == layer.c

    assert len(layer['a']) == 8
    assert len(layer['b']) == 8
    assert len(layer['c']) == 8

    assert isinstance(layer['a', 'b'], AmbiguousAttributeTupleList)
    assert isinstance(layer[['a', 'b']], AmbiguousAttributeTupleList)
    assert layer['a', 'b'] == layer[['a', 'b']]
    assert len(layer[['a', 'b']]) == 8
    assert isinstance(layer[['a']], AmbiguousAttributeTupleList)
    assert layer['a'] != layer[['a']]
    assert len(layer[['a']]) == 8


def test_advanced_indexing():
    text = Text('Mis on Sinu nimi?').analyse('morphology')
    layer = text.morph_analysis

    assert layer[:] == layer
    assert layer[2:10:2].text == ['Sinu', '?']
    assert layer[[True, False, True, False, True]].text == ['Mis', 'Sinu', '?']
    assert layer[lambda span: len(span) > 1].text == ['Mis', 'on']
    assert layer[[1, 3, 4]].text == ['on', 'nimi', '?']

    assert layer[:]['text', 'lemma'] == layer[['text', 'lemma']]
    assert layer[2:10:2, ['text', 'lemma']] == layer[2:10:2]['text', 'lemma']
    assert layer[[True, False, True, False, True], ['text', 'lemma']] == layer[True, False, True, False, True]['text', 'lemma']
    assert layer[lambda span: len(span) > 1, ['text', 'lemma']] == layer[lambda span: len(span) > 1]['text', 'lemma']
    assert layer[[1, 3, 4], ['text', 'lemma']] == layer[[1, 3, 4]]['text', 'lemma']
    assert list(layer[0, 'lemma']) == ['mis', 'mis']
    assert list(layer[0, ['lemma', 'form']][0]) == ['mis', 'pl n']
    assert list(layer[0, ['lemma', 'form']][1]) == ['mis', 'sg n']
    with pytest.raises(IndexError):
        layer[[]]


def test_check_layer_consistency():
    other_morph_layer = \
           Text('Kas?').analyse('morphology').layers['morph_analysis']
    text = Text('Kes ja kus?').analyse('morphology')
    morph_layer = text.layers['morph_analysis']
    
    # 1) Change first span, assign it to different layer
    old_first_span       = morph_layer.spans[0]
    morph_layer.spans[0] = AmbiguousSpan(layer=other_morph_layer,span=old_first_span.span)
    with pytest.raises(AssertionError) as e1:
        # Assertion error because the AmbiguousSpan is connected 
        # to different layer
        morph_layer.check_span_consistency()
    morph_layer.spans[0] = old_first_span
    morph_layer.check_span_consistency()
    
    # 2) Add element with duplicate location to the list
    morph_layer.spans.append( old_first_span )
    with pytest.raises(AssertionError) as e2:
        # Assertion error because span with duplicate location
        # exists
        morph_layer.check_span_consistency()
    morph_layer.spans.pop()
    morph_layer.check_span_consistency()
    
    # 3) Add Span instead of AmbiguousSpan
    morph_layer.spans[0] = old_first_span.span
    with pytest.raises(AssertionError) as e3:
        # Assertion error because Span was used instead 
        # of AmbiguousSpan
        morph_layer.check_span_consistency()
    morph_layer.spans[0] = old_first_span
    morph_layer.check_span_consistency()
    
    # 4) Layer with missing attributes
    layer1 = Layer(name='test_layer1',
                   attributes=['a','b','c'],
                   ambiguous=True)
    amb_span1 = AmbiguousSpan(layer=layer1, span=Span(start=0, end=1))
    layer1.spans.append( amb_span1 )
    broken_annotation = Annotation( amb_span1 )
    for attr in ['a', 'c']:
        setattr(broken_annotation, attr, '')
    layer1.spans[0].annotations.append( broken_annotation )
    with pytest.raises(AssertionError) as e4:
        # Assertion error because layer's Annotation had missing attributes
        layer1.check_span_consistency()
    #print(e4)
    
    # 5) Layer with redundant attributes
    layer1 = Layer(name='test_layer1',
                   attributes=['a'],
                   ambiguous=True)
    layer2 = Layer(name='test_layer2',
                   attributes=['a', 'b'],
                   ambiguous=True)
    amb_span1 = AmbiguousSpan(layer=layer1, span=Span(start=0, end=1))
    amb_span2 = AmbiguousSpan(layer=layer2, span=Span(start=0, end=1))
    broken_annotation = Annotation( amb_span2 )
    for attr in ['a', 'b', 'c']:
        setattr(broken_annotation, attr, '')
    amb_span1.annotations.append( broken_annotation )
    layer1.spans.append( amb_span1 )
    with pytest.raises(AssertionError) as e5:
        # Assertion error because layer's Annotation had redundant attr
        layer1.check_span_consistency()
    #print( e5 )
    
    # B1) Check for missing Span attributes
    layer = Layer(name='test_layer',
                  attributes=['a', 'b', 'c'],
                  ambiguous=False)
    span1 = Span(start=0, end=1, legal_attributes=['a', 'b'], a=1, b=11)
    span2 = Span(start=1, end=2, legal_attributes=['b', 'c'], b=11, c=21)
    layer.spans.append( span1 )
    layer.spans.append( span2 )
    with pytest.raises(AssertionError) as ex1:
        # Assertion error because Span misses some legal attributes
        layer.check_span_consistency()
    del layer.spans[-1]
    del layer.spans[-1]
    #print(ex1)

    # B2) Check for redundant Span attributes
    span3 = Span(start=0, end=1, legal_attributes=['a', 'b', 'c', 'd'], a=1, b=11, c=0, d=12)
    layer.spans.append( span3 )
    with pytest.raises(AssertionError) as ex2:
        # Assertion error because Span has a redundant attribute
        layer.check_span_consistency()
    #print(ex2)
