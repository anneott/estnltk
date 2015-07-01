# -*- coding: utf-8 -*-
"""
Estnltk prettyprinter module.

Deals with rendering Text instances as HTML.
"""
from __future__ import unicode_literals, print_function, absolute_import

try:
    from StringIO import cStringIO as StringIO
except ImportError: # Py3
    from io import StringIO

try:
    from html import escape as htmlescape
except ImportError:
    from cgi import escape as htmlescape

from estnltk import Text


class PrettyPrinter(object):
    """Class for formatting Text instances as HTML & CSS."""
    def __init__(self, **kwargs):
        asi=kwargs['asesõna']
        print(asi)
        asesõna = wordType(asi)
        return

    def render(self, text):
        text = Text(text)
        return text.get.word_texts.lemmas.postag_descriptions.as_dict

    @property
    def css(self):
        """The CSS of the prettyprinter."""
        return ''

class wordType(object):
    def __init__(self, **kwargs):
        variables = {'color': 'black', 'background': 'white', 'font': 'serif', 'weight': 'normal','italics': 'normal',
                     'underline': 'normal', 'size': 'normal', 'tracking': 'normal', 'text': ''}
        for k,v in kwargs.items():
            variables[k] = v
        self.color = variables['color']
        self.background = variables['background']
        self.font = variables['font']
        self.weight = variables['weight']
        self.italics = variables['italics']
        self.underline = variables['underline']
        self.size = variables['size']
        self.tracking = variables['tracking']
        self.text=variables['text']
        return

"""Current test protocols"""

kwargs = {'asesõna': {'text': "mis", 'color': 'red', 'size': 'large'},
          'tegusõna': {'text': "on", 'color': 'green', 'size': 'small'}}
p2 = PrettyPrinter(**kwargs)
p2Render = p2.render(p2.text)
print(p2Render['postag_descriptions'])


print(p2.asesõna.text)
print(p2.asesõna.color)
print(p2.asesõna.background)
print(p2.asesõna.font)
print(p2.asesõna.weight)
print(p2.asesõna.italics)
print(p2.asesõna.underline)
print(p2.asesõna.size)
print(p2.asesõna.tracking)