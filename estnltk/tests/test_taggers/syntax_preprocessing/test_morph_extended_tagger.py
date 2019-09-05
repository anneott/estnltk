"""MorphExtendedTagger is also tested in `estnltk/tests/test_syntax_preprocessing`

"""

from estnltk.converters import dict_to_text, dict_to_layer
from estnltk.taggers import MorphExtendedTagger


def test_morph_extended_tagger():
    text_dict = {
        'text': 'Kuhu sa lähed? Ära mine ära!',
        'meta': {},
        'layers': [{'name': 'words',
                    'attributes': ('normalized_form',),
                    'parent': None,
                    'enveloping': None,
                    'ambiguous': False,
                    'meta': {},
                    'dict_converter_module': 'default_v1',
                    'spans': [{'base_span': (0, 4), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (5, 7), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (8, 13), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (13, 14), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (15, 18), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (19, 23), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (24, 27), 'annotations': [{'normalized_form': None}]},
                              {'base_span': (27, 28), 'annotations': [{'normalized_form': None}]}]},
                   {'name': 'morph_analysis',
                    'attributes': ('lemma',
                                   'root',
                                   'root_tokens',
                                   'ending',
                                   'clitic',
                                   'form',
                                   'partofspeech'),
                    'parent': 'words',
                    'enveloping': None,
                    'ambiguous': True,
                    'dict_converter_module': 'default_v1',
                    'meta': {},
                    'spans': [{'base_span': (0, 4),
                               'annotations': [{'lemma': 'kuhu',
                                                'root': 'kuhu',
                                                'root_tokens': ('kuhu',),
                                                'ending': '0',
                                                'clitic': '',
                                                'form': '',
                                                'partofspeech': 'D'}]},
                              {'base_span': (5, 7),
                               'annotations': [{'lemma': 'sina',
                                                'root': 'sina',
                                                'root_tokens': ('sina',),
                                                'ending': '0',
                                                'clitic': '',
                                                'form': 'sg n',
                                                'partofspeech': 'P'}]},
                              {'base_span': (8, 13),
                               'annotations': [{'lemma': 'minema',
                                                'root': 'mine',
                                                'root_tokens': ('mine',),
                                                'ending': 'd',
                                                'clitic': '',
                                                'form': 'd',
                                                'partofspeech': 'V'}]},
                              {'base_span': (13, 14),
                               'annotations': [{'lemma': '?',
                                                'root': '?',
                                                'root_tokens': ('?',),
                                                'ending': '',
                                                'clitic': '',
                                                'form': '',
                                                'partofspeech': 'Z'}]},
                              {'base_span': (15, 18),
                               'annotations': [{'lemma': 'ära',
                                                'root': 'ära',
                                                'root_tokens': ('ära',),
                                                'ending': '0',
                                                'clitic': '',
                                                'form': 'neg o',
                                                'partofspeech': 'V'}]},
                              {'base_span': (19, 23),
                               'annotations': [{'lemma': 'minema',
                                                'root': 'mine',
                                                'root_tokens': ('mine',),
                                                'ending': '0',
                                                'clitic': '',
                                                'form': 'o',
                                                'partofspeech': 'V'}]},
                              {'base_span': (24, 27),
                               'annotations': [{'lemma': 'ära',
                                                'root': 'ära',
                                                'root_tokens': ('ära',),
                                                'ending': '0',
                                                'clitic': '',
                                                'form': '',
                                                'partofspeech': 'D'}]},
                              {'base_span': (27, 28),
                               'annotations': [{'lemma': '!',
                                                'root': '!',
                                                'root_tokens': ('!',),
                                                'ending': '',
                                                'clitic': '',
                                                'form': '',
                                                'partofspeech': 'Z'}]}]}]}

    expected_morph_extended_dict = {
        'name': 'morph_extended',
        'attributes': ('lemma',
                       'root',
                       'root_tokens',
                       'ending',
                       'clitic',
                       'form',
                       'partofspeech',
                       'punctuation_type',
                       'pronoun_type',
                       'letter_case',
                       'fin',
                       'verb_extension_suffix',
                       'subcat'),
        'parent': 'morph_analysis',
        'enveloping': None,
        'ambiguous': True,
        'meta': {},
        'dict_converter_module': 'default_v1',
        'spans': [{'base_span': (0, 4),
                   'annotations': [{'form': '',
                                    'letter_case': 'cap',
                                    'clitic': '',
                                    'root': 'kuhu',
                                    'fin': None,
                                    'root_tokens': ('kuhu',),
                                    'lemma': 'kuhu',
                                    'pronoun_type': None,
                                    'partofspeech': 'D',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (5, 7),
                   'annotations': [{'form': 'sg nom',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'sina',
                                    'fin': None,
                                    'root_tokens': ('sina',),
                                    'lemma': 'sina',
                                    'pronoun_type': ('ps2',),
                                    'partofspeech': 'P',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (8, 13),
                   'annotations': [{'form': 'mod indic pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': 'd',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'aux indic pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': 'd',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'main indic pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': 'd',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (13, 14),
                   'annotations': [{'form': '',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': '?',
                                    'fin': None,
                                    'root_tokens': ('?',),
                                    'lemma': '?',
                                    'pronoun_type': None,
                                    'partofspeech': 'Z',
                                    'ending': '',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': 'Int',
                                    'subcat': None}]},
                  {'base_span': (15, 18),
                   'annotations': [{'form': 'aux imper pres ps2 sg ps neg',
                                    'letter_case': 'cap',
                                    'clitic': '',
                                    'root': 'ära',
                                    'fin': True,
                                    'root_tokens': ('ära',),
                                    'lemma': 'ära',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'aux indic pres ps neg',
                                    'letter_case': 'cap',
                                    'clitic': '',
                                    'root': 'ära',
                                    'fin': True,
                                    'root_tokens': ('ära',),
                                    'lemma': 'ära',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'main indic pres ps neg',
                                    'letter_case': 'cap',
                                    'clitic': '',
                                    'root': 'ära',
                                    'fin': True,
                                    'root_tokens': ('ära',),
                                    'lemma': 'ära',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (19, 23),
                   'annotations': [{'form': 'mod indic pres ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'mod imper pres ps2 sg ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'mod imper pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'aux indic pres ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'aux imper pres ps2 sg ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'aux imper pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'main indic pres ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'main imper pres ps2 sg ps neg',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None},
                                   {'form': 'main imper pres ps2 sg ps af',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'mine',
                                    'fin': True,
                                    'root_tokens': ('mine',),
                                    'lemma': 'minema',
                                    'pronoun_type': None,
                                    'partofspeech': 'V',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (24, 27),
                   'annotations': [{'form': '',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': 'ära',
                                    'fin': None,
                                    'root_tokens': ('ära',),
                                    'lemma': 'ära',
                                    'pronoun_type': None,
                                    'partofspeech': 'D',
                                    'ending': '0',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': None,
                                    'subcat': None}]},
                  {'base_span': (27, 28),
                   'annotations': [{'form': '',
                                    'letter_case': None,
                                    'clitic': '',
                                    'root': '!',
                                    'fin': None,
                                    'root_tokens': ('!',),
                                    'lemma': '!',
                                    'pronoun_type': None,
                                    'partofspeech': 'Z',
                                    'ending': '',
                                    'verb_extension_suffix': (),
                                    'punctuation_type': 'Exc',
                                    'subcat': None}]}]}

    text = dict_to_text(text_dict)
    tagger = MorphExtendedTagger()
    tagger.tag(text)
    expected = dict_to_layer(expected_morph_extended_dict)
    assert expected == text.morph_extended, expected.diff(text.morph_extended)
