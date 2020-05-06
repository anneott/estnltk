import pytest
import pkgutil

from estnltk import Text
from estnltk.converters import dict_to_layer
from estnltk.taggers import ConllMorphTagger

udpipe_dict = {
    'name': 'udpipe_syntax',
    'text': 'Nuriseti, et hääbuvale kultuurile rõhumine mõjus pigem masendavalt ega omanud seost etnofuturismiga .',
    'meta': {},
    'parent': 'conll_morph',

    'attributes': ('id',
                   'form',
                   'lemma',
                   'upostag',
                   'xpostag',
                   'feats',
                   'head',
                   'deprel',
                   'deps',
                   'misc'),

    'enveloping': None,
    'ambiguous': True,
    'spans': [{'base_span': (0, 8),
               'annotations': [{'id': '1',
                                'form': 'Nuriseti',
                                'lemma': 'nurise',
                                'upostag': 'V',
                                'xpostag': 'V',
                                'feats': 'indic|impf|imps',
                                'head': '0',
                                'deprel': 'root',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (9, 10),
               'annotations': [{'id': '2',
                                'form': ',',
                                'lemma': ',',
                                'upostag': 'Z',
                                'xpostag': 'Z',
                                'feats': 'Com',
                                'head': '1',
                                'deprel': '@Punc',
                                'deps': '_',
                                'misc': '_'}]},
              {'base_span': (11, 13),
               'annotations': [{'id': '3',
                                'form': 'et',
                                'lemma': 'et',
                                'upostag': 'J',
                                'xpostag': 'Js',
                                'feats': '_',
                                'head': '7',
                                'deprel': '@J',
                                'deps': '_',
                                'misc': '_'}]},
              {'base_span': (14, 23),
               'annotations': [{'id': '4',
                                'form': 'hääbuvale',
                                'lemma': 'hääbuv',
                                'upostag': 'A',
                                'xpostag': 'A',
                                'feats': 'sg|all',
                                'head': '5',
                                'deprel': '@AN>',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (24, 34),
               'annotations': [{'id': '5',
                                'form': 'kultuurile',
                                'lemma': 'kultuur',
                                'upostag': 'S',
                                'xpostag': 'S',
                                'feats': 'sg|all',
                                'head': '6',
                                'deprel': '@NN>',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (35, 43),
               'annotations': [{'id': '6',
                                'form': 'rõhumine',
                                'lemma': 'rõhu=mine',
                                'upostag': 'S',
                                'xpostag': 'S',
                                'feats': 'sg|nom',
                                'head': '7',
                                'deprel': '@SUBJ',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (44, 49),
               'annotations': [{'id': '7',
                                'form': 'mõjus',
                                'lemma': 'mõju',
                                'upostag': 'V',
                                'xpostag': 'V',
                                'feats': 'indic|impf|ps3|sg',
                                'head': '1',
                                'deprel': '@FMV',
                                'deps': '_',
                                'misc': '_'}]},
              {'base_span': (50, 55),
               'annotations': [{'id': '8',
                                'form': 'pigem',
                                'lemma': 'pigem',
                                'upostag': 'D',
                                'xpostag': 'D',
                                'feats': '_',
                                'head': '9',
                                'deprel': '@ADVL',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (56, 67),
               'annotations': [{'id': '9',
                                'form': 'masendavalt',
                                'lemma': 'masendavalt',
                                'upostag': 'D',
                                'xpostag': 'D',
                                'feats': '_',
                                'head': '7',
                                'deprel': '@ADVL',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (68, 71),
               'annotations': [{'id': '10',
                                'form': 'ega',
                                'lemma': 'ega',
                                'upostag': 'J',
                                'xpostag': 'Jc',
                                'feats': '_',
                                'head': '11',
                                'deprel': '@J',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (72, 78),
               'annotations': [{'id': '11',
                                'form': 'omanud',
                                'lemma': 'oma',
                                'upostag': 'V',
                                'xpostag': 'V',
                                'feats': 'indic|impf|neg',
                                'head': '1',
                                'deprel': '@FMV',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (79, 84),
               'annotations': [{'id': '12',
                                'form': 'seost',
                                'lemma': 'seos',
                                'upostag': 'S',
                                'xpostag': 'S',
                                'feats': 'sg|part',
                                'head': '11',
                                'deprel': '@OBJ',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (85, 100),
               'annotations': [{'id': '13',
                                'form': 'etnofuturismiga',
                                'lemma': 'etno_futurism',
                                'upostag': 'S',
                                'xpostag': 'S',
                                'feats': 'sg|kom',
                                'head': '11',
                                'deprel': '@ADVL',
                                'deps': '_',
                                'misc': '_'}]},

              {'base_span': (101, 102),
               'annotations': [{'id': '14',
                                'form': '.',
                                'lemma': '.',
                                'upostag': 'Z',
                                'xpostag': 'Z',
                                'feats': 'Fst',
                                'head': '13',
                                'deprel': '@Punc',
                                'deps': '_',
                                'misc': '_'}]},
              ]}


def test_udpipe_tagger():
    from estnltk.taggers.syntax.udpipe_tagger.udpipe_tagger import UDPipeTagger
    text = Text(
        'Nuriseti , et hääbuvale kultuurile rõhumine mõjus pigem masendavalt ega omanud seost etnofuturismiga .')
    text.analyse('all')
    conll = ConllMorphTagger()
    conll.tag(text)
    tagger = UDPipeTagger()
    tagger.tag(text)
    assert dict_to_layer(udpipe_dict) == text.udpipe_syntax, text.udpipe.diff(dict_to_layer(udpipe_dict))
