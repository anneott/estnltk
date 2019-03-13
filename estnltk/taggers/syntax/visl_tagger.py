from estnltk.taggers import Tagger
from estnltk.layer.layer import Layer
from estnltk.converters.CG3_exporter import export_CG3
from estnltk.taggers.syntax.vislcg3_syntax import VISLCG3Pipeline
from estnltk import PACKAGE_PATH
import os


class VislTagger(Tagger):
    """Visl tagger"""

    conf_param = ['_visl_line_processor']

    def __init__(self, output_layer: str = 'visl', morph_extended_layer: str = 'morph_extended'):
        self.input_layers = [morph_extended_layer]
        self.output_layer = output_layer
        self.output_attributes = ['visl']

        vislcgRulesDir = os.path.relpath(os.path.join(PACKAGE_PATH, 'taggers', 'syntax', 'files'))
        vislcg_path = '/usr/bin/vislcg3'

        self._visl_line_processor = VISLCG3Pipeline(rules_dir=vislcgRulesDir, vislcg_cmd=vislcg_path).process_lines

    def _make_layer(self, text, layers, status):
        morph_extended_layer = layers[self.input_layers[0]]

        layer = Layer(name=self.output_layer, text_object=text, attributes=self.output_attributes,
                      parent=morph_extended_layer._base, ambiguous=True)

        visl_output = self._visl_line_processor(export_CG3(text))

        visl_lines = []
        token_in_progress = False
        for line in visl_output.split('\n'):
            if line and line[0] == '\t':
                if token_in_progress:
                    visl_lines[-1].append(line.strip())
                else:
                    visl_lines.append([line.strip()])
                    token_in_progress = True
            else:
                token_in_progress = False

        for token_lines, span in zip(visl_lines, morph_extended_layer):
            for token_line in token_lines:
                layer.add_annotation(span, visl=token_line)
        return layer