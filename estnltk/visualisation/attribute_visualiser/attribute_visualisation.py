from IPython.display import display_html
from estnltk.visualisation.attribute_visualiser.direct_attribute_visualiser import DirectAttributeVisualiser
from estnltk.visualisation.core.span_decomposition import decompose_to_elementary_spans
from estnltk.core import rel_path
from estnltk.layer_operations import merge_layers


class DisplayAttributes:
    """Superclass for attribute visualisers"""

    js_file = rel_path("visualisation/attribute_visualiser/prettyprinter.js")
    css_file = rel_path("visualisation/attribute_visualiser/prettyprinter.css")
    html_displayed = False
    original_layer = None
    accepted_array = None
    chosen_annotations = None

    def __init__(self, name=""):
        self.span_decorator = DirectAttributeVisualiser(text_id=str(name))
        self.name = name

    def __call__(self, layer):
        display_html(self.html_output(layer), raw=True)
        self.original_layer = layer

    def html_output(self, layer):
        segments, span_list = decompose_to_elementary_spans(layer, layer.text_object.text)

        outputs = [self.css()]
        outputs.append(self.event_handler_code())

        for segment in segments:
            outputs.append(self.span_decorator(segment, span_list).replace("\n", "<br>"))

        outputs.append('<button onclick="export_data(')
        outputs.append("'")
        outputs.append(self.name)
        outputs.append("'")
        outputs.append(')">Export data</button>')
        self.html_displayed = True
        return "".join(outputs)

    def css(self):
        with open(self.css_file) as css_file:
            contents = css_file.read()
            output = ''.join(["<style>\n", contents, "</style>"])
        return output

    def event_handler_code(self):
        with open(self.js_file) as js_file:
            contents = js_file.read()
            output = ''.join(["<script>\n var text_id='", str(self.name), "'\n", contents, "</script>"])
        return output

    def delete_chosen_spans(self):
        new_layer = self.mark_chosen_spans()
        if new_layer is None:
            return None
        for i, span in enumerate(new_layer):
            for j, annotation in enumerate(span.annotations):
                if not annotation.approved:
                    del new_layer[i].annotations[j]
        return new_layer

    def mark_chosen_spans(self):
        if not self.html_displayed:
            print("HTML of this attribute visualiser hasn't been displayed yet!"
                  " Call this visualiser with a layer as an argument to do it.")
            return None

        if self.accepted_array is None:
            print("The annotation choices weren't saved! Click \"Export data\" to do it!")
            return None

        attribute_list = list(self.original_layer.attributes)
        attribute_list.append("approved")
        new_layer = merge_layers(layers=[self.original_layer],
                                 output_layer='new_layer',
                                 output_attributes=attribute_list)
        for i, accept_value in enumerate(self.accepted_array.split(" ")):
            chosen_annotations = accept_value.split(",")
            for j, val in enumerate(chosen_annotations):
                if val != '':
                    if int(val) == 2:
                        new_layer.spans[i].annotations[j].approved = False
                    else:
                        new_layer.spans[i].annotations[j].approved = True

        return new_layer
