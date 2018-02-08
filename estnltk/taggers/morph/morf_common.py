#
#  Provides common functions, variables and constants for modules 
#  using Vabamorf-based morphological processing.
# 

from estnltk.text import Span

# Default parameters to be passed to Vabamorf
# Note: these defaults are from  estnltk.vabamorf.morf
DEFAULT_PARAM_DISAMBIGUATE = True
DEFAULT_PARAM_GUESS        = True
DEFAULT_PARAM_PROPERNAME   = True
DEFAULT_PARAM_PHONETIC     = False
DEFAULT_PARAM_COMPOUND     = True

# Morphological analysis attributes used by Vabamorf
VABAMORF_ATTRIBUTES = ('root', 'ending', 'clitic', 'form', 'partofspeech')

# Morphological analysis attributes used by ESTNLTK
ESTNLTK_MORPH_ATTRIBUTES = ('lemma', 'root', 'root_tokens', 'ending', 'clitic', 'form', 'partofspeech')

# Name of the ignore attribute. During the morphological 
# disambiguation, all spans of "morph_analysis" that have 
# ignore attribute set to True will be skipped;
IGNORE_ATTR = '_ignore'

# =================================
#    Helper functions
# =================================

def _get_word_text( word:Span ):
    '''Returns a word string corresponding to the given (word) Span. 
       If the normalized word form is available, returns the normalized 
       form instead of the surface form. 
        
       Parameters
       ----------
       word: Span
          word which text (or normalized text) needs to be acquired;
            
       Returns
       -------
       str
          normalized text of the word, or word.text
    '''
    if hasattr(word, 'normalized_form') and word.normalized_form != None:
        # return the normalized version of the word
        return word.normalized_form
    else:
        return word.text


def _create_empty_morph_span( word, layer_attributes = None ):
    ''' Creates an empty 'morph_analysis' span that will 
        have word as its parent span. 
        All attribute values of the span will be set 
        to None.
        
        Returns the Span.
    '''
    current_attributes = \
        layer_attributes if layer_attributes else ESTNLTK_MORPH_ATTRIBUTES
    span = Span(parent=word)
    for attr in current_attributes:
        setattr(span, attr, None)
    return span


def _is_empty_span( span:Span ):
    '''Checks if the given span (from the layer 'morph_analysis')
       is empty, that is: all of its morph attributes are set to 
       None. 
       This means that the word was unknown to morphological 
       analyser. 
    '''
    all_none = [getattr(span, attr) is None for attr in ESTNLTK_MORPH_ATTRIBUTES]
    return all(all_none)



# ========================================================
#    Utils for converting Vabamorf dict <-> EstNLTK Span
# ========================================================

def _convert_morph_analysis_span_to_vm_dict( span:Span ):
    ''' Converts a SpanList from the layer 'morph_analysis'
        into a dictionary object that has the structure
        required by the Vabamorf:
        { 'text' : ..., 
          'analysis' : [
             { 'root': ..., 
               'partofspeech' : ..., 
               'clitic': ... ,
               'ending': ... ,
               'form': ... ,
             },
             ...
          ]
        }
        Returns the dictionary.
    '''
    attrib_dicts = {}
    # Get lists corresponding to attributes
    for attr in ESTNLTK_MORPH_ATTRIBUTES:
        attrib_dicts[attr] = getattr(span, attr)
    # Rewrite attributes in Vabamorf's analysis format
    # Collect analysis dicts
    nr_of_analyses = len(attrib_dicts['lemma'])
    word_dict = { 'text' : span.text[0], \
                  'analysis' : [] }
    for i in range( nr_of_analyses ):
        analysis = {}
        for attr in attrib_dicts.keys():
            attr_value = attrib_dicts[attr][i]
            if attr == 'root_tokens':
                attr_value = list(attr_value)
            analysis[attr] = attr_value
        word_dict['analysis'].append(analysis)
    return word_dict


def _convert_vm_dict_to_morph_analysis_spans( vm_dict, word, \
                                              layer_attributes = None, \
                                              sort_analyses = True ):
    ''' Converts morphological analyses from the Vabamorf's 
        dictionary format to the EstNLTK's Span format, and 
        attaches the newly created span as a child of the 
        word.
        
        If sort_analyses=True, then analyses will be sorted 
        by root,ending,clitic,postag,form;
        
        Note: if word has no morphological analyses (e.g. it 
        is an unknown word), then returns an empty list.
        
        Returns a list of EstNLTK's Spans.
    '''
    spans = []
    current_attributes = \
        layer_attributes if layer_attributes else ESTNLTK_MORPH_ATTRIBUTES
    word_analyses = vm_dict['analysis']
    if sort_analyses:
        # Sort analyses ( to assure a fixed order, e.g. for testing purpose )
        word_analyses = sorted( vm_dict['analysis'], key = \
            lambda x: x['root']+x['ending']+x['clitic']+x['partofspeech']+x['form'], 
            reverse=False )
    for analysis in word_analyses:
        span = Span(parent=word)
        for attr in current_attributes:
            if attr in analysis:
                # We have a Vabamorf's attribute
                if attr == 'root_tokens':
                    # make it hashable for Span.__hash__
                    setattr(span, attr, tuple(analysis[attr]))
                else:
                    setattr(span, attr, analysis[attr])
            else:
                # We have an extra attribute -- initialize with None
                setattr(span, attr, None)
        spans.append(span)
    return spans

