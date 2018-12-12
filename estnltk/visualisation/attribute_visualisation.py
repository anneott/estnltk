from IPython.display import display_html
from estnltk.visualisation.direct_attribute_visualiser import DirectAttributeVisualiser
from estnltk.visualisation.prettyprinter import decompose_to_elementary_spans

class DisplayAttributes:

    def __init__(self):
        self.span_decorator = DirectAttributeVisualiser()
        display_html(self.span_decorator.css())

    def __call__(self, layer):
        display_html(self.html_output(layer), raw=True)

    def html_output(self, layer):
        segments = decompose_to_elementary_spans(layer, layer.text_object.text)

        outputs = []
        for segment in segments:
            outputs.append(self.span_decorator(segment))

        print(outputs)
        self.span_decorator.css_added=False
        self.span_decorator.js_added=False
        return "".join(outputs)