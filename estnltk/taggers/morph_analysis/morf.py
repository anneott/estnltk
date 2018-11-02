#
#  Provides Vabamorf-based morphological analysis and disambiguation.
#
#  VabamorfTagger can be used for end-to-end morphological processing.
#  Alternatively, the process can be broken down into substeps, using 
#  VabamorfAnalyzer, PostMorphAnalysisTagger and VabamorfDisambiguator.
# 
from typing import MutableMapping, Any

from estnltk.text import Layer, Span, SpanList, Text
from estnltk.layer.ambiguous_span import AmbiguousSpan

from estnltk.taggers import TaggerOld
from estnltk.vabamorf.morf import Vabamorf
from estnltk.taggers import PostMorphAnalysisTagger, Retagger

from estnltk.taggers.morph_analysis.morf_common import DEFAULT_PARAM_DISAMBIGUATE, DEFAULT_PARAM_GUESS
from estnltk.taggers.morph_analysis.morf_common import DEFAULT_PARAM_PROPERNAME, DEFAULT_PARAM_PHONETIC
from estnltk.taggers.morph_analysis.morf_common import DEFAULT_PARAM_COMPOUND
from estnltk.taggers.morph_analysis.morf_common import ESTNLTK_MORPH_ATTRIBUTES
from estnltk.taggers.morph_analysis.morf_common import VABAMORF_ATTRIBUTES
from estnltk.taggers.morph_analysis.morf_common import IGNORE_ATTR

from estnltk.taggers.morph_analysis.morf_common import _get_word_text, _create_empty_morph_span
from estnltk.taggers.morph_analysis.morf_common import _span_to_records_excl
from estnltk.taggers.morph_analysis.morf_common import _is_empty_span

from estnltk.taggers.morph_analysis.morf_common import _convert_morph_analysis_span_to_vm_dict
from estnltk.taggers.morph_analysis.morf_common import _convert_vm_dict_to_morph_analysis_spans


class VabamorfTagger(TaggerOld):
    description   = "Tags morphological analysis on words. Uses Vabamorf's morphological analyzer and disambiguator."
    layer_name    = None
    attributes    = ESTNLTK_MORPH_ATTRIBUTES
    depends_on    = None
    configuration = None

    def __init__(self,
                 layer_name='morph_analysis',
                 postanalysis_tagger=None,
                 **kwargs):
        """Initialize VabamorfTagger class.

        Note: Keyword arguments 'disambiguate', 'guess', 'propername',
        'phonetic' and 'compound' can be used to override the default 
        configuration of Vabamorf's morphological analyser. See the 
        description of VabamorfAnalyzer.tag method for details on
        configuration arguments.
        
        Parameters
        ----------
        layer_name: str (default: 'morph_analysis')
            Name of the layer where analysis results are stored.
        postanalysis_tagger: estnltk.taggers.Retagger (default: PostMorphAnalysisTagger())
            Retagger that is used to post-process "morph_analysis" layer after
            it is created (and before it is disambiguated).
            This tagger corrects morphological analyses, prepares morpho-
            logical analyses for disambiguation (if required) and fills in 
            values of extra attributes in morph_analysis Spans.
        """
        # Check if the user has provided a custom postanalysis_tagger
        if not postanalysis_tagger:
            # Initialize default postanalysis_tagger
            postanalysis_tagger = PostMorphAnalysisTagger(output_layer=layer_name)
        
        self.kwargs = kwargs
        self.layer_name = layer_name
       
        if postanalysis_tagger:
            # Check for Retagger
            assert isinstance(postanalysis_tagger, Retagger), \
                '(!) postanalysis_tagger should be of type estnltk.taggers.Retagger.'
            # Check for layer match
            assert hasattr(postanalysis_tagger, 'output_layer'), \
                '(!) postanalysis_tagger does not define output_layer.'
            assert postanalysis_tagger.output_layer == self.layer_name, \
                '(!) postanalysis_tagger should modify layer "'+str(self.layer_name)+'".'+\
                ' Currently, it modifies layer "'+str(postanalysis_tagger.output_layer)+'".'
            assert hasattr(postanalysis_tagger, 'attributes'), \
                '(!) postanalysis_tagger does not define any attributes.'
        self.postanalysis_tagger = postanalysis_tagger
        vm_instance = Vabamorf.instance()
        # Initialize morf analyzer and disambiguator; 
        # Also propagate layer names to submodules;
        self.vabamorf_analyser      = VabamorfAnalyzer( vm_instance=vm_instance,
                                                        layer_name=layer_name )
        self.vabamorf_disambiguator = VabamorfDisambiguator( vm_instance=vm_instance,
                                                             output_layer=layer_name )

        self.configuration = {'postanalysis_tagger':self.postanalysis_tagger.__class__.__name__, }
        #                      'vabamorf_analyser':self.vabamorf_analyser.__class__.__name__,
        #                      'vabamorf_disambiguator':self.vabamorf_disambiguator.__class__.__name__ }
        self.configuration.update(self.kwargs)

        self.depends_on = ['words', 'sentences']
        # Update dependencies: add dependencies specific to postanalysis_tagger
        if postanalysis_tagger and postanalysis_tagger.depends_on:
            for postanalysis_dependency in postanalysis_tagger.depends_on:
                if postanalysis_dependency not in self.depends_on and \
                   postanalysis_dependency != self.layer_name:
                    self.depends_on.append(postanalysis_dependency)


    def tag(self, text: Text, return_layer=False) -> Text:
        """Anayses given Text object morphologically. 
        
        Note: exact configuration of the analysis (e.g. 
        whether guessing of unknown words will be performed, 
        or whether analyses will be disambiguated) depends on 
        the initialization parameters of the class.
        
        Parameters
        ----------
        text: estnltk.text.Text
            Text object that is to be analysed morphologically.
            The Text object must have layers 'words', 'sentences'.
        return_layer: boolean (default: False)
            If True, then the new layer is returned; otherwise 
            the new layer is attached to the Text object, and the 
            Text object is returned;

        Returns
        -------
        Text or Layer
            If return_layer==True, then returns the new layer, 
            otherwise attaches the new layer to the Text object 
            and returns the Text object;
        """
        # Fetch parameters ( if missing, use the defaults )
        disambiguate = self.kwargs.get('disambiguate', DEFAULT_PARAM_DISAMBIGUATE)
        guess        = self.kwargs.get('guess',        DEFAULT_PARAM_GUESS)
        propername   = self.kwargs.get('propername',   DEFAULT_PARAM_PROPERNAME)
        phonetic     = self.kwargs.get('phonetic',     DEFAULT_PARAM_PHONETIC)
        compound     = self.kwargs.get('compound',     DEFAULT_PARAM_COMPOUND)
        # --------------------------------------------
        #   Morphological analysis
        # --------------------------------------------
        self.vabamorf_analyser.tag( text, \
                                    guess=guess,\
                                    propername=propername,\
                                    phonetic=phonetic, \
                                    compound=compound )
        morph_layer = text[self.layer_name]
        # --------------------------------------------
        #   Post-processing
        # --------------------------------------------
        if self.postanalysis_tagger:
            # Post-analysis tagger is responsible for:
            # 1) Retagging "morph_analysis" layer with post-corrections;
            # 2) Adding and filling in extra_attributes in "morph_analysis" layer;
            self.postanalysis_tagger.retag(text)
        # --------------------------------------------
        #   Morphological disambiguation
        # --------------------------------------------
        if disambiguate:
            self.vabamorf_disambiguator.retag(text)
        # --------------------------------------------
        #   Return layer or Text
        # --------------------------------------------
        # Return layer
        if return_layer:
            delattr(text, self.layer_name) # Remove layer from the text
            morph_layer._bound = False
            return morph_layer
        # Layer is already attached to the text, return it
        return text


# ========================================================
#    Util: find a matching morphological analysis 
#          record from a list of records;
# ========================================================

def _find_matching_old_record( new_record, old_records ):
    '''Finds a record from old_records that matches the morphological 
       analyses attributes of the new record. Returns the matching
       record, or None, if matching record was not found.
       Two records are considered as matching if all of their 
       VABAMORF_ATTRIBUTES's values are equal;
        
       Parameters
       ----------
       new_record: dict
           a record which match from old_records will be sought;

       old_records: list of dict
           list of old records from which a matching records will 
           be sought;

       Returns
       -------
       dict
           matching record from old_records, or None, if no matching 
           record was found;
    '''
    assert old_records is not None
    for old_record in old_records:
        attr_matches = []
        for attr in VABAMORF_ATTRIBUTES:
            attr_match = \
                 (old_record.get(attr,None) == new_record.get(attr,None))
            attr_matches.append( attr_match )
        if all( attr_matches ):
            # Return matching old record
            return old_record
    return None


# ========================================================
#    Check if the span is to be ignored during 
#          the morphological disambiguation
# ========================================================

def _is_ignore_span( span ):
    ''' Checks if the given span (from the layer 'morph_analysis')
        has attribute IGNORE_ATTR, and whether all of its values 
        are True (which means: the span should be ignored). 
        
        Note: if some values are True, and others are False or None, 
        then throws an Exception because partial ignoring is 
        currently not implemented.
    '''
    if hasattr( span, IGNORE_ATTR ):
        ignore_values = getattr(span, IGNORE_ATTR)
        if ignore_values and all(ignore_values):
            return True
        if ignore_values and any(ignore_values):
            # Only some of the Spans have ignore=True, but 
            # partial ignoring is currently not implemented
            raise Exception('(!) Partial ignoring is currently not '+\
                            'implemented. Unexpected ignore attribute '+\
                            "values encountered at the 'morph_analysis' "+\
                            'span '+str((span.start,span.end))+'.')
    return False


# ===============================
#    VabamorfAnalyzer
# ===============================

class VabamorfAnalyzer(TaggerOld):
    description   = "Analyzes texts morphologically. Uses Vabamorf's analyzer. "+\
                    "Note: resulting analyses can be ambiguous. "
    layer_name    = None
    attributes    = VabamorfTagger.attributes
    depends_on    = None
    configuration = None
    
    def __init__(self,
                 layer_name='morph_analysis',
                 extra_attributes=None,
                 vm_instance=None,
                 **kwargs):
        """Initialize VabamorfAnalyzer class.

        Parameters
        ----------
        layer_name: str (default: 'morph_analysis')
            Name of the layer where analysis results are stored.
        extra_attributes: list of str (default: None)
            List containing names of extra attributes that will be 
            attached to Spans. All extra attributes will be 
            initialized to None.
        vm_instance: estnltk.vabamorf.morf.Vabamorf
            An instance of Vabamorf that is to be used for analysing
            text morphologically.
        """
        self.kwargs = kwargs
        if vm_instance:
            self.vm_instance = vm_instance
        else:
            self.vm_instance  = Vabamorf.instance()
        self.extra_attributes = extra_attributes
        self.layer_name = layer_name
        
        self.configuration = { 'vm_instance':self.vm_instance.__class__.__name__ }
        if self.extra_attributes:
            self.configuration['extra_attributes'] = self.extra_attributes
        self.configuration.update(self.kwargs)

        self.depends_on = ['words', 'sentences']


    def _get_wordlist(self, text:Text):
        ''' Returns a list of words from given text. If normalized word 
            forms are available, uses normalized forms instead of the 
            surface forms. '''
        result = []
        for word in text.words:
            result.append( _get_word_text( word ) )
        return result


    def tag(self, text: Text,
                  return_layer=False,
                  propername=DEFAULT_PARAM_PROPERNAME,
                  guess     =DEFAULT_PARAM_GUESS,
                  compound  =DEFAULT_PARAM_COMPOUND,
                  phonetic  =DEFAULT_PARAM_PHONETIC ) -> Text:
        """Anayses given Text object morphologically. 
        
        Note: disambiguation is not performed, so the results of
        analysis will (most likely) be ambiguous.
        
        Parameters
        ----------
        text: estnltk.text.Text
            Text object that is to be analysed morphologically.
            The Text object must have layers 'words', 'sentences'.
        return_layer: boolean (default: False)
            If True, then the new layer is returned; otherwise 
            the new layer is attached to the Text object, and the 
            Text object is returned;
        propername: boolean (default: True)
            Propose additional analysis variants for proper names 
            (a.k.a. proper name guessing).
        guess: boolean (default: True)
            Use guessing in case of unknown words.
        compound: boolean (default: True)
            Add compound word markers to root forms.
        phonetic: boolean (default: False)
            Add phonetic information to root forms.

        Returns
        -------
        Text or Layer
            If return_layer==True, then returns the new layer, 
            otherwise attaches the new layer to the Text object 
            and returns the Text object;
        """
        # --------------------------------------------
        #   Use Vabamorf for morphological analysis
        # --------------------------------------------
        kwargs = {
            "disambiguate": False,  # perform analysis without disambiguation
            "guess"     : guess,
            "propername": propername,
            "compound"  : compound,
            "phonetic"  : phonetic,
        }
        # Perform morphological analysis sentence by sentence
        word_spans = text['words'].span_list
        word_span_id = 0
        analysis_results = []
        for sentence in text['sentences'].span_list:
            # A) Collect all words inside the sentence
            sentence_words = []
            while word_span_id < len(word_spans):
                span = word_spans[word_span_id]
                if sentence.start <= span.start and \
                    span.end <= sentence.end:
                    # Word is inside the sentence
                    sentence_words.append( \
                        _get_word_text( span ) 
                    )
                    word_span_id += 1
                elif sentence.end <= span.start:
                    break
            # B) Use Vabamorf for analysis 
            #    (but check length limitations first)
            if len(sentence_words) > 15000:
                # if 149129 < len(wordlist) on Linux,
                # if  15000 < len(wordlist) < 17500 on Windows,
                # then self.instance.analyze(words=wordlist, **self.kwargs) raises
                # RuntimeError: CFSException: internal error with vabamorf
                for i in range(0, len(sentence_words), 15000):
                    analysis_results.extend( self.vm_instance.analyze(words=sentence_words[i:i+15000], **kwargs) )
            else:
                analysis_results.extend( self.vm_instance.analyze(words=sentence_words, **kwargs) )

        # Assert that all words obtained an analysis 
        # ( Note: there must be empty analyses for unknown 
        #         words if guessing is not used )
        assert len(text.words) == len(analysis_results), \
            '(!) Unexpectedly the number words ('+str(len(text.words))+') '+\
            'does not match the number of obtained morphological analyses ('+str(len(analysis_results))+').'

        # --------------------------------------------
        #   Store analysis results in a new layer     
        # --------------------------------------------
        # A) Create layer
        morph_attributes = self.attributes
        current_attributes = morph_attributes
        if self.extra_attributes:
            for extra_attr in self.extra_attributes:
                current_attributes = current_attributes + (extra_attr,)
        morph_layer = Layer(name=self.layer_name,
                            parent='words',
                            ambiguous=True,
                            attributes=current_attributes )
        # B) Populate layer        
        for word, analyses_dict in zip(text.words, analysis_results):
            # Convert from Vabamorf dict to a list of Spans 
            spans = \
                _convert_vm_dict_to_morph_analysis_spans( \
                        analyses_dict, \
                        word, \
                        layer_attributes=current_attributes, \
                        sort_analyses = True )
            # Attach spans (if word has morphological analyses)
            for span in spans:
                morph_layer.add_span( span )
            if not spans:
                # if word has no morphological analyses (e.g.
                # it is an unknown word), then attach an 
                # empty Span as a placeholder
                empty_span = \
                    _create_empty_morph_span( \
                        word, \
                        layer_attributes=current_attributes )
                morph_layer.add_span( empty_span )

        # --------------------------------------------
        #   Return layer or Text
        # --------------------------------------------
        if return_layer:
            return morph_layer
        text[self.layer_name] = morph_layer
        return text

# ===============================
#    VabamorfDisambiguator
# ===============================

class VabamorfDisambiguator(Retagger):
    """Disambiguates morphologically analysed texts. 
       Uses Vabamorf for disambiguating.
    """
    attributes    = VabamorfTagger.attributes
    conf_param = ['depends_on', '_vm_instance']

    def __init__(self,
                 output_layer='morph_analysis',
                 vm_instance=None):
        """Initialize VabamorfDisambiguator class.

        Parameters
        ----------
        output_layer: str (default: 'morph_analysis')
            Name of the morphological analysis layer. 
            This is the layer where the disambiguation will
            be performed;
        vm_instance: estnltk.vabamorf.morf.Vabamorf
            An instance of Vabamorf that is to be used for 
            disambiguating text morphologically;
        """
        # Set attributes & configuration
        self.output_layer = output_layer
        self.input_layers = ['words', 'sentences', output_layer]
        self.depends_on = self.input_layers
        if vm_instance:
            self._vm_instance = vm_instance
        else:
            self._vm_instance = Vabamorf.instance()



    def _change_layer(self, raw_text: str, layers: MutableMapping[str, Layer], status: dict = None) -> None:
        """Performs morphological disambiguation, and replaces ambiguous 
           morphological analyses with their disambiguated variants.
           
           Also, removes the temporary attribute '_ignore' from the 
           the 'morph_analysis' layer.

           Parameters
           ----------
           raw_text: str
              Text string corresponding to the text which will be 
              morphologically disambiguated;
              
           layers: MutableMapping[str, Layer]
              Layers of the raw_text. Contains mappings from the name 
              of the layer to the Layer object.  The  mapping  must 
              contain layers 'words', 'sentences', and 'morph_analysis'. 
              The layer 'morph_analysis' will be retagged.
              
           status: dict
              This can be used to store metadata on layer retagging.
        """
        # --------------------------------------------
        #  Check for existence of required layers     
        #  Collect layer's attributes                 
        # --------------------------------------------
        assert self.output_layer in layers
        assert 'sentences' in layers
        assert 'words' in layers
        # Take attributes from the input layer
        current_attributes = layers[self.output_layer].attributes
        # Check if there are any extra attributes to carry over
        # from the old layer
        extra_attributes = []
        for cur_attr in current_attributes:
            if cur_attr not in self.attributes and \
               cur_attr != IGNORE_ATTR:
                extra_attributes.append( cur_attr )
        # Check that len(word_spans) >= len(morph_spans)
        morph_spans = layers[self.output_layer].spans
        word_spans  = layers['words'].span_list
        assert len(word_spans) >= len(morph_spans), \
            '(!) Unexpectedly, the number of elements at the layer '+\
                 '"'+str(self.output_layer)+'" is greater than the '+\
                 'number of elements at the layer "words". There '+\
                 'should be one to one correspondence between '+\
                 'the layers.'
        # --------------------------------------------
        #  Disambiguate sentence by sentence
        # --------------------------------------------
        sentence_start_morph_span_id = 0
        morph_span_id = 0
        word_span_id  = 0
        for sentence in layers['sentences'].span_list:
            # A) Collect all words/morph_analyses inside the sentence
            #    Assume: len(word_spans) >= len(morph_spans)
            sentence_word_spans  = []
            sentence_morph_spans = []
            sentence_morph_dicts = []
            words_missing_morph  = []
            ignored_word_ids     = set()
            sentence_start_morph_span_id = morph_span_id
            while word_span_id < len(word_spans):
                # Get corresponding word span
                word_span  = word_spans[word_span_id]
                morph_span = None
                if sentence.start <= word_span.start and \
                    word_span.end <= sentence.end:
                    morphFound = False
                    # Get corresponding morph span
                    if morph_span_id < len(morph_spans):
                        morph_span = morph_spans[morph_span_id]
                        if word_span.start == morph_span.start and \
                           word_span.end == morph_span.end and \
                           not _is_empty_span( morph_span.spans[0] ):
                            # Word & morph found: collect items
                            sentence_word_spans.append( word_span )
                            sentence_morph_spans.append( morph_span )
                            if not _is_ignore_span( morph_span ):
                                # Add the dict only if it is not marked as 
                                # to be ignored 
                                word_morph_dict = \
                                    _convert_morph_analysis_span_to_vm_dict( \
                                        morph_span )
                                sentence_morph_dicts.append( word_morph_dict )
                            else:
                                # Remember that this word was ignored during 
                                # the disambiguation
                                ignored_word_ids.add( len(sentence_word_spans)-1 )
                            # Advance positions
                            morph_span_id += 1
                            word_span_id  += 1
                            morphFound = True
                    if not morphFound:
                        # Did not find any morph analysis for the word
                        words_missing_morph.append( word_span )
                        word_span_id  += 1
                        # Advance morph position, if morph was empty
                        if morph_span and _is_empty_span(morph_span.spans[0]):
                            morph_span_id += 1
                elif sentence.end <= word_span.start:
                    # Word falls out of the sentence: break
                    break
            # B) Validate that all words have morphological analyses;
            #    If not (e.g. guessing was switched off while analysing), 
            #    then we cannot perform the disambiguation;
            if words_missing_morph:
                missing_pos = [(w.start, w.end) for w in words_missing_morph]
                raise Exception('(!) Unable to perform morphological disambiguation '+\
                                'because words at positions '+str(missing_pos)+' '+\
                                'have no morphological analyses.')
            # C) Use Vabamorf for disambiguation
            disambiguated_dicts = []
            if sentence_morph_dicts:
                disambiguated_dicts = self._vm_instance.disambiguate(sentence_morph_dicts)
            # D) Convert Vabamorf's results to AmbiguousSpans
            global_morph_span_id = sentence_start_morph_span_id
            wid = 0
            morph_dict_id = 0
            while wid < len(sentence_word_spans):
                # D.0) Find corresponding analysis_dict
                while wid in ignored_word_ids:
                    # Skip the ignored words: they should preserve the 
                    # same analyses as in the input
                    global_morph_span_id += 1
                    wid += 1
                if not wid < len(sentence_word_spans):
                    # Break if ignoring has passed sentence boundaries
                    break
                
                # D.0) Get comparable morphological analyses for the word
                # Old morphological analyses (ambiguous):
                old_morph_records = \
                    [ _span_to_records_excl(span, [IGNORE_ATTR]) for span in sentence_morph_spans[wid] ]
                # New morphological analyses (disambiguated):
                disambiguated_records = disambiguated_dicts[morph_dict_id]['analysis']

                # D.1) Convert records back to AmbiguousSpans
                ambiguous_span = \
                    AmbiguousSpan(layer=morph_spans[global_morph_span_id].layer, \
                                  span=morph_spans[global_morph_span_id].span)
                
                # D.1) Rewrite records into a proper format, and 
                #      add to the span
                
                # Sort analyses ( to assure a fixed order, e.g. for testing purpose )
                disambiguated_records = sorted( disambiguated_records, key = \
                         lambda x: x['root']+x['ending']+x['clitic']+x['partofspeech']+x['form'], 
                         reverse=False )
                for analysis_record in disambiguated_records:
                    new_record = {}
                    # Fill in attributes of the record
                    for attr in current_attributes:
                        if attr in analysis_record:
                            # We have a Vabamorf's attribute
                            if attr == 'root_tokens':
                                # make it hashable for Span.__hash__
                                new_record[attr] = tuple(analysis_record[attr])
                            else:
                                new_record[attr] = analysis_record[attr]
                        else:
                            # We have an extra attribute -- initialize with None
                            new_record[attr] = None
                    if extra_attributes:
                        # Carry over attribute values (if needed)
                        matching_old_record = \
                            _find_matching_old_record( new_record, old_morph_records )
                        if matching_old_record:
                            for ex_attrib in extra_attributes:
                                new_record[ex_attrib] = matching_old_record[ex_attrib]
                        else:
                            raise Exception('(!) Unable to find a matching record for '+\
                                    str(new_record)+' from '+str(old_morph_records))
                    # Add new record to the ambiguous span
                    ambiguous_span.add_annotation( **new_record )

                # D.2) Rewrite the old span with the new one
                morph_spans[global_morph_span_id] = ambiguous_span
                
                # Advance indices
                global_morph_span_id += 1
                morph_dict_id += 1
                wid += 1
        # --------------------------------------------
        #  Post-processing:
        #  Remove IGNORE_ATTR from the output layer
        # --------------------------------------------
        if IGNORE_ATTR in layers[self.output_layer].attributes:
            new_attributes = ()
            for old_attrib in layers[self.output_layer].attributes:
                if old_attrib != IGNORE_ATTR:
                    new_attributes += (old_attrib,)
            layers[self.output_layer].attributes = new_attributes
            morph_spans = layers[self.output_layer].spans
            for ms_id, morph_span in enumerate(morph_spans):
                for span in morph_span.spans:
                    delattr( span, IGNORE_ATTR )


