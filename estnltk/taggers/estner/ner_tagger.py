from estnltk.taggers import Tagger
from estnltk.core import DEFAULT_PY3_NER_MODEL_DIR
from estnltk.taggers.estner.refac.ner import ModelStorageUtil
from estnltk.taggers.estner.fex import FeatureExtractor
from estnltk.taggers.estner import CrfsuiteModel
from estnltk.layer.layer import Layer
from estnltk import EnvelopingBaseSpan
from typing import MutableMapping
from estnltk.text import Text


class NerTagger(Tagger):
    """The class for tagging named entities."""
    conf_param = ['modelUtil', 'nersettings', 'fex', 'crf_model']

    def __init__(self, model_dir=DEFAULT_PY3_NER_MODEL_DIR, output_layer='ner', morph_layer_input=('morph_analysis',)):
        """Initialize a new NerTagger instance.

        Parameters
        ----------
        model_dir: st
            A directory containing a trained ner model and a settings file.
        output_layer: str
            Name of the layer that will be added to the text object
        morph_layer_input: tuple
            Names of the morphological analysis layers used in feature extraction

        """
        self.output_layer = output_layer
        self.output_attributes = ["nertag"]
        modelUtil = ModelStorageUtil(model_dir)
        nersettings = modelUtil.load_settings()
        self.input_layers = morph_layer_input
        self.fex = FeatureExtractor(nersettings, self.input_layers)
        self.crf_model = CrfsuiteModel(settings=nersettings,
                                       model_filename=modelUtil.model_filename)

    def _make_layer(self, text: Text, layers: MutableMapping[str, Layer], status: dict) -> Layer:
        # prepare input for nertagger
        self.fex.process([text])
        snt_labels = self.crf_model.tag(text)
        flattened = (word for snt in snt_labels for word in snt)

        # add the labels
        nerlayer = Layer(name=self.output_layer, attributes=self.output_attributes, text_object=text,
                         enveloping="words")
        entity_spans = []
        entity_type = None
        for span, label in zip(text.words, flattened):
            if entity_type is None:
                entity_type = label[2:]
            if label == "O":
                if entity_spans:
                    nerlayer.add_annotation(EnvelopingBaseSpan(entity_spans),
                                            **{self.output_attributes[0]: entity_type})
                    entity_spans = []
                continue
            if label[0] == "B" or entity_type != label[2:]:
                if entity_spans:
                    nerlayer.add_annotation(EnvelopingBaseSpan(entity_spans),
                                            **{self.output_attributes[0]: entity_type})
                    entity_spans = []
            entity_type = label[2:]
            entity_spans.append(span.base_span)
        text.pop_layer("ner_features")
        return nerlayer