import unittest
import os
from unittest import TestCase

from estnltk import Text
from estnltk.taggers.neural_morph.new_neural_morph.neural_morph_tagger import NeuralMorphTagger, load_model
from estnltk.neural_morph.new_neural_morph import softmax
from estnltk.neural_morph.new_neural_morph import seq2seq
from estnltk.neural_morph.new_neural_morph.vabamorf_2_neural import neural_model_tags

# os.environ['NEURAL_MORPH_TAGGER_CONFIG'] = "/home/kermos/projects/estnltk/estnltk/neural_morph/new_neural_morph/seq2seq/emb_cat_sum/config.py"
NEURAL_MORPH_TAGGER_CONFIG = os.environ.get('NEURAL_MORPH_TAGGER_CONFIG')

skip_reason = "Environment variable NEURAL_MORPH_TAGGER_CONFIG is not defined."


class DummyTagger:
    def predict(self, snt_words, snt_analyses):
        tags = []
        for word, analyses in zip(snt_words, snt_analyses):
            assert len(analyses) > 0
            tag = analyses[0]
            tags.append(tag)
        return tags


class TestDummyTagger(TestCase):
    def test(self):
        tagger = NeuralMorphTagger(DummyTagger())
        text = Text("Ära mine sinna.")
        text.tag_layer(["morph_analysis"])
        tagger.tag(text)

        for word, morf_pred in zip(text.words, text.neural_morph_analysis):
            morf_true = neural_model_tags(word.text, word.morph_analysis['partofspeech'][0], word.morph_analysis['form'][0])[0]
            self.assertEqual(morf_pred.morphtag, morf_true)


def test_sentences(filename):
    file = open(filename)
    words, tags, analyses = [], [], []
    line = file.readline()
    
    while line:
        if line.strip() == "":
            yield words, tags, analyses
            words, tags, analyses = [], [], []
        else:
            items = line.strip().split("\t")
            word, tag, word_analyses = items[0], items[1], items[2:]
            words.append(word)
            tags.append(tag)
            analyses.append(word_analyses)
            
        line = file.readline()
        
    if len(words) > 0:
        yield words, tags, analyses
    file.close()


if NEURAL_MORPH_TAGGER_CONFIG is not None:
    if "softmax" in NEURAL_MORPH_TAGGER_CONFIG:
        model_module = softmax
    else:
        model_module = seq2seq
    os.environ['OUT_DIR'] = os.path.join(os.path.dirname(NEURAL_MORPH_TAGGER_CONFIG), "output")
    model = load_model(model_module, NEURAL_MORPH_TAGGER_CONFIG)


@unittest.skipIf(NEURAL_MORPH_TAGGER_CONFIG is None, skip_reason)
class TestNeuralModel(TestCase):
    def test(self):
        word_count = 0
        correct_count = 0
        sentences = test_sentences("neural_test_sentences.txt")
        
        for words, tags, analyses in sentences:
            word_count += len(words)
            
            preds = model.predict(words, analyses)
            for tag, prediction in zip(tags, preds):
                if tag == prediction:
                    correct_count += 1
                    
        self.assertTrue(correct_count/word_count >= 0.97)
                    

@unittest.skipIf(NEURAL_MORPH_TAGGER_CONFIG is None, skip_reason)
class TestNeuralTagger(TestCase):  
    def test(self):
        tagger = NeuralMorphTagger(model)
        sentences = test_sentences("neural_test_sentences.txt")
        
        word_count = 0
        correct_count = 0
        
        for words, tags, analyses in sentences:
            text = Text(" ".join(words))
            text.tag_layer(['morph_analysis'])
            tagger.tag(text)
            
            self.assertTrue(tagger.output_layer in text.layers)
            self.assertTrue(hasattr(text.words[0], 'morphtag'))
            
            word_count += len(tags)
            
            for word, tag in zip(text.words, tags):
                if word.morphtag == tag:
                    correct_count += 1
                    
        self.assertTrue(correct_count/word_count >= 0.97)