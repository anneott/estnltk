from typing import Container

from estnltk.text import Text
from estnltk.layer.layer import Layer
from estnltk.layer.annotation import Annotation
from estnltk.converters.serialisation_modules import layer_dict_converter


def dict_to_annotation(span, annotation_dict: dict):
    return Annotation(span, **annotation_dict)


def dict_to_layer(layer_dict: dict, text: Text = None, detached_layers=None) -> Layer:
    return layer_dict_converter.dict_to_layer(layer_dict, text)


def dict_to_text(text_dict: dict, layers: Container = None) -> Text:
    text = Text(text_dict['text'])
    text.meta = text_dict['meta']
    for layer_dict in text_dict['layers']:
        if layers is None or layer_dict['name'] in layers:
            layer = dict_to_layer(layer_dict, text)
            text.add_layer(layer)
    return text
