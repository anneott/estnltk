from estnltk.text import Layer
from estnltk.layer_operations import resolve_conflicts


def test_resolve_conflicts_MAX():
    # empty span list
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [] == [(span.start, span.end) for span in layer]

    # one span
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  4, '_priority_': 0},
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [(1, 4)] == [(span.start, span.end) for span in layer]

    # equal spans
    layer = Layer(name='test_layer', attributes=['_priority_'], ambiguous=True)
    layer = layer.from_records([[{'start': 1, 'end':  4, '_priority_': 0},
                                 {'start': 1, 'end':  4, '_priority_': 0},
                               ]])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert len(layer[0]) == 1
    assert [(1, 4)] == [(span.start, span.end) for span in layer]

    # common start
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  4, '_priority_': 0},
                                {'start': 1, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [(1, 6)] == [(span.start, span.end) for span in layer]

    # common end
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 3, 'end':  6, '_priority_': 0},
                                {'start': 1, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [(1, 6)] == [(span.start, span.end) for span in layer]

    # complex
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 0},
                                {'start': 2, 'end':  4, '_priority_': 0},
                                {'start': 3, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [(1, 8)] == [(span.start, span.end) for span in layer]

    # complex, different priorities
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 1},
                                {'start': 2, 'end':  4, '_priority_': 0},
                                {'start': 3, 'end':  6, '_priority_': 1}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MAX', priority_attribute='_priority_')
    assert [(2, 4)] == [(span.start, span.end) for span in layer]


def test_resolve_conflicts_MIN():    
    # empty span list
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [] == [(span.start, span.end) for span in layer]

    # one span
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  4, '_priority_': 0},
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [(1, 4)] == [(span.start, span.end) for span in layer]

    # equal spans
    layer = Layer(name='test_layer', attributes=['_priority_'], ambiguous=True)
    layer = layer.from_records([[{'start': 1, 'end':  4, '_priority_': 0},
                                 {'start': 1, 'end':  4, '_priority_': 0},
                               ]])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert len(layer[0]) == 1
    assert [(1, 4)] == [(span.start, span.end) for span in layer]

    # common start
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  4, '_priority_': 0},
                                {'start': 1, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [(1, 4)] == [(span.start, span.end) for span in layer]

    # common end
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 3, 'end':  6, '_priority_': 0},
                                {'start': 1, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [(3, 6)] == [(span.start, span.end) for span in layer]

    # complex
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 0},
                                {'start': 2, 'end':  4, '_priority_': 0},
                                {'start': 3, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [(2, 4)] == [(span.start, span.end) for span in layer]

    # complex, different priorities
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 1},
                                {'start': 2, 'end':  4, '_priority_': 1},
                                {'start': 3, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='MIN', priority_attribute='_priority_')
    assert [(3, 6)] == [(span.start, span.end) for span in layer]


def test_resolve_conflicts_ALL():
    # complex
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 0},
                                {'start': 2, 'end':  4, '_priority_': 0},
                                {'start': 3, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='ALL', priority_attribute='_priority_')
    assert [(1, 8), (2, 4), (3, 6)] == [(span.start, span.end) for span in layer]

    # complex, different priorities
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  8, '_priority_': 1},
                                {'start': 2, 'end':  4, '_priority_': 1},
                                {'start': 3, 'end':  6, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='ALL', priority_attribute='_priority_')
    assert [(3, 6)] == [(span.start, span.end) for span in layer]

    # complex, different priorities
    layer = Layer(name='test_layer', attributes=['_priority_'])
    layer = layer.from_records([{'start': 1, 'end':  3, '_priority_': 2},
                                {'start': 2, 'end':  7, '_priority_': 1},
                                {'start': 4, 'end':  8, '_priority_': 0}
                               ])
    layer = resolve_conflicts(layer, conflict_resolving_strategy='ALL', priority_attribute='_priority_')
    assert [(1, 3), (4, 8)] == [(span.start, span.end) for span in layer]


def test_resolve_conflicts_ambiguous_layer():
    # keep_equal=True
    layer = Layer(name='test_layer', attributes=['attr_1', '_priority_'], ambiguous=True)
    layer = layer.from_records([
        [{'start': 1, 'end': 2, 'attr_1': 1, '_priority_': 0}],
        [{'start': 2, 'end': 3, 'attr_1': 1, '_priority_': 1},
         {'start': 2, 'end': 3, 'attr_1': 2, '_priority_': 2},
         {'start': 2, 'end': 3, 'attr_1': 3, '_priority_': 3},
         {'start': 2, 'end': 3, 'attr_1': 4, '_priority_': 4}],
        [{'start': 4, 'end': 5, 'attr_1': 1, '_priority_': 1},
         {'start': 4, 'end': 5, 'attr_1': 2, '_priority_': 1},
         {'start': 4, 'end': 5, 'attr_1': 3, '_priority_': 0},
         {'start': 4, 'end': 5, 'attr_1': 4, '_priority_': 0}],
        [{'start': 6, 'end': 7, 'attr_1': 1, '_priority_': 2},
         {'start': 6, 'end': 7, 'attr_1': 2, '_priority_': 1},
         {'start': 6, 'end': 7, 'attr_1': 3, '_priority_': 2},
         {'start': 6, 'end': 7, 'attr_1': 4, '_priority_': 3}],
    ])
    layer = resolve_conflicts(layer,
                              conflict_resolving_strategy='ALL',
                              priority_attribute='_priority_',
                              keep_equal=True)

    result = [(span.start, span.end) for aspan in layer for span in aspan]
    assert [(1, 2), (2, 3), (4, 5), (4, 5), (6, 7)] == result, result

    # keep_equal=False
    layer = Layer(name='test_layer', attributes=['attr_1', '_priority_'], ambiguous=True)
    layer = layer.from_records([
        [{'start': 1, 'end': 4, 'attr_1': 1, '_priority_': 0}],
        [{'start': 3, 'end': 6, 'attr_1': 1, '_priority_': 1},
         {'start': 3, 'end': 6, 'attr_1': 2, '_priority_': 2},
         {'start': 3, 'end': 6, 'attr_1': 3, '_priority_': 3},
         {'start': 3, 'end': 6, 'attr_1': 4, '_priority_': 4}],
        [{'start': 5, 'end': 7, 'attr_1': 1, '_priority_': 1},
         {'start': 5, 'end': 7, 'attr_1': 2, '_priority_': 1},
         {'start': 5, 'end': 7, 'attr_1': 3, '_priority_': 0},
         {'start': 5, 'end': 7, 'attr_1': 4, '_priority_': 0}],
    ]
    )
    layer = resolve_conflicts(layer,
                              conflict_resolving_strategy='ALL',
                              priority_attribute='_priority_',
                              keep_equal=False)
    assert [(1, 4), (5, 7)] == [(span.start, span.end) for aspan in layer for span in aspan]