from estnltk.layer.annotation import Annotation
from estnltk.layer.layer import Layer
from estnltk.text import Text
from estnltk.converters.serialisation_modules import layer_dict_converter


def annotation_to_dict(annotation: Annotation) -> dict:
    if isinstance(annotation, Annotation):
        return dict(annotation)
    raise TypeError('expected Annotation, got {}'.format(type(annotation)))


def layer_to_dict(layer: Layer) -> dict:
    return layer_dict_converter.layer_to_dict(layer)


def text_to_dict(text: Text) -> dict:
    assert isinstance(text, Text), type(text)
    text_dict = {'text': text.text,
                 'meta': text.meta,
                 'layers': []}
    for layer in text.list_layers():
        text_dict['layers'].append(layer_dict_converter.layer_to_dict(layer))
    return text_dict
