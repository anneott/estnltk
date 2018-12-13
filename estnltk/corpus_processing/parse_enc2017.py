#
#  Module for converting Estonian National Corpus (ENC) 2017 documents 
#  to EstNLTK Text objects.
#
#  The Estonian National Corpus (ENC) 2017 contains variety of corpora,
#  including documents crawled from web (etTenTen 2013 and etTenTen 2017),
#  documents from the National Corpus (e.g. Estonian Reference Corpus), 
#  and articles from Estonian Wikipedia.
#
#  Documents are in an XML-like format, contain metadata (e.g  document 
#  source and title), and have been split into subdocuments and sentences, 
#  or into paragraphs and sentences.
#  etTenTen 2017 web documents have been crawled with the tool SpiderLing, 
#  see http://corpus.tools/wiki/SpiderLing for details. Most of the textual 
#  content should be clean from HTML annotations, but some annotations may 
#  have remained.
#

import re

from estnltk.text import Text, Layer, EnvelopingSpan

from estnltk.taggers import TokensTagger, CompoundTokenTagger, WordTagger
from estnltk.taggers import SentenceTokenizer, ParagraphTokenizer

# =================================================
#   Helpful utils
# =================================================

# Pattern for capturing names & values of attributes
enc_tag_attrib_pat = re.compile('([^= ]+)="([^"]+?)"')

def parse_tag_attributes( tag_str ):
    """Extracts names & values of attributes from an XML tag string,
       and returns as a dictionary.
       Throws an Exception if attribute key appears more than once.
       Parameters
       ----------
       tag_str: str
           string representation of an XML tag;
        
       Returns
       -------
       dict
           a dictionary with attribute-value pairs;
    """
    assert tag_str.count('"') % 2 == 0, \
        '(!) Uneven number of quotation marks in: '+str(tag_str)
    attribs = {}
    for attr_match in enc_tag_attrib_pat.finditer(tag_str):
        key   = attr_match.group(1)
        value = attr_match.group(2)
        if key in attribs:
           raise Exception(' (!) Unexpected: attribute "'+key+'" appears more than once in: '+tag_str)
        attribs[key] = value
    return attribs


def extract_doc_ids_from_corpus_file( in_file, encoding='utf-8' ):
    '''Opens a prevert corpus file, reads its content, and extracts 
       all document id-s. 
       Returns a list of document id-s (list of strings).
       
       Parameters
       ----------
       in_file: str
           Full name of the corpus file (name with path);
           
       encoding: str
           Encoding of in_file. Defaults to 'utf-8';
       
       Returns
       -------
       list of str
           a list of extracted document id-s;
    '''
    enc_doc_tag_start = re.compile("<doc[^<>]+>")
    doc_ids = []
    with open( in_file, mode='r', encoding=encoding ) as f:
        for line in f:
            stripped_line = line.strip()
            m_doc_start = enc_doc_tag_start.search(stripped_line)
            if m_doc_start: 
                attribs = parse_tag_attributes( stripped_line )
                assert 'id' in attribs.keys()
                doc_ids.append( attribs['id'] )
    return doc_ids


# =================================================
#   Reconstructing EstNLTK Text objects
# =================================================

class ENC2017TextReconstructor:
    """ ENC2017TextReconstructor builds Estnltk Text objects 
        based on document contents extracted by PrevertXMLFileParser.
    """
    NOT_METADATA_KEYS = ['_paragraphs','_sentences','_words','_original_words']
    
    def __init__(self, tokenization='preserve',
                       paragraph_separator='\n\n', \
                       sentence_separator =' ', \
                       word_separator=' ', \
                       layer_name_prefix='' ):
        '''Initializes the parser.
        
           Parameters
           ----------
           tokenization: ['none', 'preserve', 'estnltk']
                Specifies if tokenization will be added to created Texts, 
                and if so, then how it will be added. 
                Three options:
                * 'none'     -- text   will   be   created  without  any 
                                tokenization layers;
                * 'preserve' -- original tokenization from XML files will 
                                be preserved in layers of the text; 
                * 'estnltk'  -- text's original tokenization will be 
                                overwritten by estnltk's tokenization;
               (default: 'preserve')
           paragraph_separator: str
               String that will be used for separating paragraphs in 
               the reconstructed text;
               Default: '\n\n'
           sentence_separator: str
               String that will be used for separating sentences in 
               the reconstructed text;
               Default: ' '
           word_separator: str
               String that will be used for separating words in the 
               reconstructed text;
               Default: ' '
           layer_name_prefix: str
               Prefix that will be added to names of created layers
               in the reconstructed text if original tokenization is
               preserved (tokenization == 'preserve');
               Default: ''
        '''
        assert isinstance(paragraph_separator, str)
        assert isinstance(sentence_separator, str)
        assert isinstance(word_separator, str)
        assert isinstance(layer_name_prefix, str)
        assert tokenization in [None, 'none', 'preserve', 'estnltk'], \
            '(!) Unknown tokenization option: {!r}'.format(tokenization)
        if not tokenization:
            tokenization = 'none'
        self.tokenization        = tokenization
        self.paragraph_separator = paragraph_separator
        self.sentence_separator  = sentence_separator
        self.word_separator      = word_separator
        self.layer_name_prefix   = layer_name_prefix



    def reconstruct_text( self, doc_dict ):
        '''Reconstructs Text object based on dictionary representation
           of the document (doc_dict).
        '''
        # 0. Collect attribute names 
        par_attribs = self._collect_attribute_names( doc_dict, '_paragraphs' )
        s_attribs   = self._collect_attribute_names( doc_dict, '_sentences' )
        # 1. Reconstruct text string
        #    Collect locations of paragraphs, sentences, words
        sent_locations       = []
        para_locations       = []
        word_locations       = []
        word_chunk_locations = [] # word chunks are bigger than words
        cur_pos = 0
        all_text_tokens = []
        if '_paragraphs' in doc_dict:
            # --------------------------------------------------------
            paragraphs = doc_dict['_paragraphs']
            for pid, paragraph in enumerate(paragraphs):
                p_start = cur_pos
                if '_sentences' in paragraph:
                    # Collect sentences and words
                    cur_pos, sent_locations, word_locations, \
                    word_chunk_locations, all_text_tokens = \
                        self._collect_sentences_and_words( paragraph,
                                                           cur_pos,
                                                           sent_locations,
                                                           word_locations,
                                                           word_chunk_locations,
                                                           all_text_tokens,
                                                           s_attribs )
                p_end = cur_pos
                # Record paragraph
                # 1) Create record
                record = {'start':p_start, 'end':p_end}
                # 2) Collect paragraph's attributes
                if par_attribs:
                    for attrib in par_attribs:
                        record[attrib] = \
                            paragraph[attrib] if attrib in paragraph else None
                # 3) Store record
                para_locations.append( record )
                if pid+1 < len(paragraphs):
                    all_text_tokens.append(self.paragraph_separator)
                    cur_pos += len(self.paragraph_separator)
        elif '_sentences' in doc_dict:
            # --------------------------------------------------------
            cur_pos, sent_locations, word_locations, \
            word_chunk_locations, all_text_tokens = \
                self._collect_sentences_and_words( doc_dict,
                                                   cur_pos,
                                                   sent_locations,
                                                   word_locations,
                                                   word_chunk_locations,
                                                   all_text_tokens,
                                                   s_attribs )
        # --------------------
        # Note: if input document's annotations are malformed, like 
        #       in case of the document with id=1175371, then there 
        #       will be both '_paragraphs' and '_sentences' in the 
        #       doc_dict.  Currently,  only  '_paragraphs'  will be 
        #       extracted in such situations ...
        # --------------------
        # 2) Reconstruct text 
        text = Text( ''.join(all_text_tokens) )
        # 3) Add metadata
        for key in doc_dict.keys():
            if key not in self.NOT_METADATA_KEYS:
                text.meta[key] = doc_dict[key]
        # 4) Create tokenization layers (if required)
        if self.tokenization == 'preserve':
            # Preserve original tokenization layers
            # Attach layers to the Text obj
            self._create_original_layers( text, para_locations, sent_locations, \
                                          word_locations, word_chunk_locations, \
                                          s_attribs, par_attribs )
        elif self.tokenization == 'estnltk':
            # Create tokenization with estnltk's default tools
            # ( overwrites the original tokenization )
            text.tag_layer(['tokens', 'compound_tokens'])
            text.tag_layer(['words', 'sentences', 'paragraphs'])
        return text



    def _collect_attribute_names( self, doc_dict, segmentation ):
        '''Collects  all  legal  attribute  names  used  in  doc_dict
           for given segmentation (either '_paragraphs' or '_sentences').
        '''
        assert segmentation in ['_paragraphs', '_sentences']
        attribs = set()
        parent = None
        # 1) '_paragraphs' or '_sentences' inside doc_dict
        if segmentation in doc_dict:
            for segment in doc_dict[segmentation]:
                for key in segment.keys():
                    attribs.add(key)
        # 2) '_sentences' inside '_paragraphs'
        elif segmentation == '_sentences' and \
           '_paragraphs' in doc_dict:
            for paragraph in doc_dict['_paragraphs']:
                if segmentation in paragraph:
                    for segment in paragraph[segmentation]:
                        for key in segment.keys():
                            attribs.add(key)
        # Remove redundant keys:
        for rkey in self.NOT_METADATA_KEYS:
            if rkey in attribs:
                attribs.remove(rkey)
        return attribs



    def _collect_sentences_and_words( self, content_dict,
                                            cur_pos,
                                            sent_locations,
                                            word_locations,
                                            word_chunk_locations,
                                            all_text_tokens,
                                            sent_attribs ):
        '''Collects content of '_sentences', '_original_words' and 
           '_words' from given content_dict.
           
           Records token locations into sent_locations, word_locations
           and word_chunk_locations, and updates the pointer cur_pos.
           
           Adds tokens that should go into reconstructable text string
           into list all_text_tokens.
        '''
        assert '_sentences' in content_dict
        sentences = content_dict['_sentences']
        for sid, sentence in enumerate(sentences):
            s_start = cur_pos
            local_word_chunk_locations = []
            if '_original_words' in sentence:
                # Collect words from sentence
                words = sentence['_original_words']
                for wid, word in enumerate(words):
                    w_start = cur_pos
                    w_end   = cur_pos+len(word)
                    cur_pos += len(word)
                    local_word_chunk_locations.append( \
                        {'start':w_start, 'end':w_end} )
                    all_text_tokens.append( word )
                    if wid+1 < len(words):
                        all_text_tokens.append(self.word_separator)
                        cur_pos += len(self.word_separator)
                word_chunk_locations.extend(local_word_chunk_locations)
            if '_words' in sentence:
                last_cur_pos = cur_pos
                cur_pos = s_start
                # Collect subwords/tokens from sentence
                words = sentence['_words']
                for wid, word in enumerate(words):
                    w_start = cur_pos
                    w_end   = cur_pos+len(word)
                    cur_pos += len(word)
                    word_locations.append( \
                        {'start':w_start, 'end':w_end} )
                    # Check if given word is inside a bigger word chunk
                    inside_chunk = False
                    for chunk in word_chunk_locations:
                        if chunk['start'] <= w_start and \
                           chunk['end'] > w_end:
                            inside_chunk = True
                            break
                    if wid+1 < len(words) and not inside_chunk:
                        cur_pos += len(self.word_separator)
                cur_pos = last_cur_pos
            s_end = cur_pos
            # Create sentence record
            record = {'start':s_start, 'end':s_end}
            # Collect attributes
            if sent_attribs:
                for attrib in sent_attribs:
                    record[attrib] = \
                        sentence[attrib] if attrib in sentence else None
            # Record sentence
            sent_locations.append( record )
            if sid+1 < len(sentences):
                all_text_tokens.append(self.sentence_separator)
                cur_pos += len(self.sentence_separator)
        return cur_pos, sent_locations, word_locations, \
               word_chunk_locations, all_text_tokens



    def _create_original_layers( self, text_obj,
                                 para_locations,
                                 sent_locations,
                                 word_locations,
                                 word_chunk_locations,
                                 sent_extra_attribs, 
                                 para_extra_attribs,
                                 attach_layers=True ):
        '''Creates Text object layers based on given locations 
           of original paragraphs, sentences, words, and 
           word chunks.
           
           If attach_layers=True, attaches created layer to the 
           text_obj (default), otherwise, returns the list of 
           created layers.
           
           Note: if the input document is empty (has no words,
           sentences nor paragraphs), no layers will be created.
        '''
        assert isinstance(text_obj, Text)
        orig_word_chunks     = None
        orig_tokens          = None
        orig_compound_tokens = None
        orig_words           = None
        orig_sentences       = None
        orig_paragraphs      = None
        # Create word chunks layer
        if word_chunk_locations is not None and len(word_chunk_locations) > 0:
            orig_word_chunks = \
                Layer(name=self.layer_name_prefix+'word_chunks', \
                      attributes=(), \
                      text_object=text_obj,\
                      ambiguous=False).from_records( word_chunk_locations )
        # Create words layer from the token records
        if word_locations is not None and len(word_locations) > 0:
            # Create tokens layer
            orig_tokens = \
                Layer(name=self.layer_name_prefix+TokensTagger.output_layer, \
                      attributes=(), \
                      text_object=text_obj,\
                      ambiguous=False).from_records( word_locations )
            # Create compound tokens layer
            # Note: this layer will remain empty, as there is no information
            #       about compound tokens in the original text
            orig_compound_tokens = \
                Layer(name=self.layer_name_prefix+CompoundTokenTagger.output_layer, \
                      enveloping=orig_tokens.name, \
                      attributes=CompoundTokenTagger.output_attributes, \
                      text_object=text_obj,\
                      ambiguous=False)
            # Create words layer
            orig_words = \
                Layer(name=self.layer_name_prefix+WordTagger.output_layer, \
                      attributes=WordTagger.output_attributes, \
                      text_object=text_obj,\
                      ambiguous=False).from_records( word_locations )
        # Create sentences layer enveloping around words
        if sent_locations is not None and len(sent_locations) > 0 and \
           orig_words is not None: 
            s_attributes = SentenceTokenizer.output_attributes
            if sent_extra_attribs:
                for attrib in sent_extra_attribs:
                    s_attributes += (attrib,)
            orig_sentences = Layer(name=self.layer_name_prefix+SentenceTokenizer.output_layer, \
                                   enveloping=orig_words.name, \
                                   attributes=s_attributes, \
                                   text_object=text_obj,\
                                   ambiguous=False)
            sid = 0; s_start = -1; s_end = -1
            for wid, word in enumerate(orig_words):
                if sid > len(sent_locations):
                    break
                sentence = sent_locations[sid]
                if word.start == sentence['start']:
                    s_start = wid
                if word.end == sentence['end']:
                    s_end = wid
                if s_start != -1 and s_end != -1:
                    current_sent_attribs={}
                    if sent_extra_attribs:
                          for attrib in sent_extra_attribs:
                              current_sent_attribs[attrib] = \
                                  sentence[attrib] if attrib in sentence else None
                    span = EnvelopingSpan(spans=orig_words[s_start:s_end+1].spans, \
                                          attributes=current_sent_attribs)
                    orig_sentences.add_span(span)
                    sid += 1; s_start = -1; s_end = -1
            orig_sentences.check_span_consistency()
            assert sid == len(sent_locations)
        # Create paragraphs layer enveloping around sentences
        if para_locations is not None and len(para_locations) > 0 and \
           orig_sentences is not None:
            p_attributes = ParagraphTokenizer.output_attributes
            if para_extra_attribs:
                for attrib in para_extra_attribs:
                    p_attributes += (attrib,)
            orig_paragraphs = Layer(name=self.layer_name_prefix+ParagraphTokenizer.output_layer, \
                                    enveloping=orig_sentences.name, \
                                    attributes=p_attributes, \
                                    text_object=text_obj, \
                                    ambiguous=False)
            pid = 0; p_start = -1; p_end = -1
            for sid, sentence in enumerate(orig_sentences):
               if pid > len(para_locations):
                  break
               paragraph = para_locations[pid]
               if sentence.start == paragraph['start']:
                  p_start = sid
               if sentence.end == paragraph['end']:
                  p_end = sid
               if p_start != -1 and p_end != -1:
                  current_paragraph_attribs={}
                  if para_extra_attribs:
                      for attrib in para_extra_attribs: 
                          current_paragraph_attribs[attrib] = \
                              paragraph[attrib] if attrib in paragraph else None
                  span = EnvelopingSpan(spans=orig_sentences[p_start:p_end+1].spans,
                                        attributes=current_paragraph_attribs)
                  orig_paragraphs.add_span(span)
                  pid += 1; p_start = -1; p_end = -1
            orig_paragraphs.check_span_consistency()
            assert pid == len(para_locations)
        created_layers = [orig_word_chunks, orig_tokens, orig_compound_tokens, 
                          orig_words, orig_sentences, orig_paragraphs]
        if attach_layers:
            for layer in created_layers:
                if layer is not None:
                    text_obj[layer.name] = layer
        else:
            return layers



# =================================================
#   Parsing ENC 2017 corpus files
# =================================================

class PrevertXMLFileParser:
    """ A very simple XMLParser that allows line by line parsing of prevert type 
        XML files. The parser maintains the state and reconstructs a Text object 
        whenever a single document from XML has been completely parsed.
        
        This parser takes advantage of the simple structure of the input XML 
        files: all XML tags are on separate lines, so the line by line parsing 
        is actually the most straightforward approach.
        
        * PrevertXMLFileParser is made for parsing prevert files of ENC 2017; 
          the implementation is based on earlier EtTenTenXMLParser;
        * prevert is an output file type used by the SpiderLing web crawler, 
          see http://corpus.tools/wiki/SpiderLing for details; 
    """


    def __init__(self, focus_ids=None,\
                       focus_srcs=None,\
                       focus_lang=None,\
                       discard_empty_fragments=True, \
                       store_fragment_attributes=True, \
                       add_unknown_tags_to_words=True, \
                       textreconstructor=None ):
        '''Initializes the parser.
        
           Parameters
           ----------
           focus_ids: set of str
               Set of document id-s corresponding to the documents which 
               need to be extracted from the XML content.
               If provided, then only documents with given id-s will be 
               parsed, and all other documents will be skipped.
               If None or empty, then all documents in the content will 
               be parsed.
               Important note: ids must be given as strings, not as 
               integers.
           focus_srcs: set of str
               Set of document src-s corresponding to subcorpora from 
               which documents need to be extracted from the XML content.
               If provided, then only documents that have a src value from
               the set will be extracted, and all other documents will 
               be skipped.
               If None or empty, then all documents in the content will 
               be parsed.
           focus_lang: set of str
               Set of allowed document languages.
               If provided, then only documents that have a lang value from
               the set will be extracted, and all other documents will 
               be skipped. Note that if focus_lang is set, but the document
               does not have lang attribute, the document will also be 
               skipped;
               If None or empty, then all documents in the content will 
               be parsed.
           discard_empty_fragments: boolean
               If set, then empty text fragments -- documents, paragraphs and 
               sentences -- will be discarded.
               (default: True)
           store_fragment_attributes: boolean
               If set, then attributes in the XML tag of a paragraph or sentence 
               will be collected and added as attributes of the corresponding 
               layer in Text object.
               (default: True)
           add_unknown_tags_to_words: boolean
               If set, then unknown tags will be added to the reconstructed text 
               as words. Otherwise, an exception will be thrown if an unknown tag 
               will be encountered.
               (default: True)
           textreconstructor: ENC2017TextReconstructor
               ENC2017TextReconstructor instance that can be used for reconstructing
               the Text object based on extracted document content;
               Default: None
        '''
        # Initialize the state of parsing
        self.lines            = 0
        self.inside_focus_doc = False
        self.document         = {} # metadata of the document
        self.content          = {} # content of the document or subdocument
        self.last_was_glue = False
        if focus_ids is not None:
            assert isinstance(focus_ids, set)
            if len(focus_ids) == 0:
                focus_ids = None
        self.focus_doc_ids = focus_ids
        if focus_srcs is not None:
            assert isinstance(focus_srcs, set)
            if len(focus_srcs) == 0:
                focus_srcs = None
        self.focus_srcs = focus_srcs
        if focus_lang is not None:
            assert isinstance(focus_lang, set)
            if len(focus_lang) == 0:
                focus_lang = None
        self.focus_lang                = focus_lang
        self.store_fragment_attributes = store_fragment_attributes
        self.discard_empty_fragments   = discard_empty_fragments
        self.add_unknown_tags_to_words = add_unknown_tags_to_words
        self.textreconstructor         = textreconstructor
        # Patterns for detecting tags
        self.enc_doc_tag_start  = re.compile("^<doc[^<>]+>\s*$")
        self.enc_doc_tag_end    = re.compile("^</doc>\s*$")
        # Info tags: used for marking subdocuments inside documents
        self.enc_info_tag_start = re.compile("^<info[^<>]+>\s*$")
        self.enc_info_tag_end   = re.compile("^</info>\s*$")
        self.enc_p_tag_start    = re.compile("^<p( [^<>]+)?>\s*$")
        self.enc_p_tag_end      = re.compile("^</p>\s*$")
        self.enc_s_tag_start    = re.compile("^<s( [^<>]+)?>\s*$")
        self.enc_s_tag_end      = re.compile("^</s>\s*$")
        self.enc_glue_tag       = re.compile("^<g/>$")
        self.enc_unknown_tag    = re.compile("^<([^<>]+)>$")



    def parse_next_line( self, line: str ):
        '''Parses a next line from the XML content of ENC_2017 corpus.
        
           If an end of document is reached with the line, there a two 
           possibilities.
           First, if textreconstructor is set, reconstructs and returns 
           Text object based on the seen document. Second, if 
           textreconstructor is not set, returns dict representation
           of the the seen document. 
           And if the line is not definitive, but just continues 
           the document content, returns None.
           
           If focus_doc_ids was provided, then only documents which
           id-s are in the set focus_doc_ids will be extracted.
        '''
        stripped_line = line.strip()
        m_doc_start   = self.enc_doc_tag_start.match(stripped_line)
        m_doc_end     = self.enc_doc_tag_end.match(stripped_line)
        # *** Start of a new document
        if m_doc_start: 
            # Clear old doc content
            self.document.clear()
            self.content.clear()
            # Carry over attributes
            attribs = parse_tag_attributes( stripped_line )
            for key, value in attribs.items():
                if key in ['_paragraphs','_sentences','_words','_original_words']:
                   raise Exception("(!) Improper key name "+key+" in tag <doc>.")
                self.document[key] = value
            # Check if the document passes filters: id, src, lang
            doc_filters_passed = []
            if self.focus_doc_ids is not None:
                doc_filters_passed.append( self.document['id'] in self.focus_doc_ids )
            if self.focus_srcs is not None:
                doc_filters_passed.append( 'src' in self.document and \
                                           self.document['src'] in self.focus_srcs )
            if self.focus_lang is not None:
                doc_filters_passed.append( 'lang' in self.document and \
                                           self.document['lang'] in self.focus_lang )
            # Include document to processing only if there were no filters or
            # if all filters were successfully passed 
            if not doc_filters_passed or all( doc_filters_passed ):
                self.inside_focus_doc = True
        # *** End of a document
        if m_doc_end and self.inside_focus_doc:
            self.inside_focus_doc = False
            if 'subdoc' in self.content:
                # If document consisted of subdocuments, then we are finished
                self.lines += 1
                return None
            else:
                if self.discard_empty_fragments:
                    # Check that the document is not empty
                    if '_sentences' not in self.content and \
                       '_paragraphs' not in self.content:
                        # if the document had no content, discard it ...
                        self.lines += 1
                        return None
                # Carry over metadata attributes
                for key, value in self.document.items():
                    assert key not in self.content, \
                        ('(!) Key {!r} already in {!r}.').format( key, self.content.keys() )
                    self.content[key] = value
                self.lines += 1
                if self.textreconstructor:
                    # create Text object
                    text_obj = self.textreconstructor.reconstruct_text( self.content )
                    return text_obj
                else:
                    return self.content
        # Skip document if it is not one of the focus documents
        if not self.inside_focus_doc:
            self.lines += 1
            return None
        # Next patterns to be checked
        m_info_start  = self.enc_info_tag_start.match(stripped_line)
        m_info_end    = self.enc_info_tag_end.match(stripped_line)
        m_par_start   = self.enc_p_tag_start.match(stripped_line)
        m_par_end     = self.enc_p_tag_end.match(stripped_line)
        m_s_start     = self.enc_s_tag_start.match(stripped_line)
        m_s_end       = self.enc_s_tag_end.match(stripped_line)
        m_glue        = self.enc_glue_tag.match(stripped_line)
        m_unk_tag     = self.enc_unknown_tag.match(stripped_line)
        # *** New subdocument (info)
        if m_info_start:
            # Assert that some content from the doc tag has already been read
            assert 'id' in self.document
            info_attribs = parse_tag_attributes( stripped_line )
            # Create a new subdocument
            if 'subdoc' in self.content:
                self.content['subdoc'].clear()
            else:
                self.content['subdoc'] = {}
            # 1) Carry over subdocument attributes
            for key, value in info_attribs.items():
                if key == 'id':
                    # Rename 'id' -> 'subdoc_id'
                    key = 'subdoc_id'
                if key in ['_paragraphs','_sentences','_words','_original_words']:
                    raise Exception("(!) Improper key name "+key+" in tag <doc>.")
                self.content['subdoc'][key] = value
            # 2) Carry over parent document's attributes
            for key, value in self.document.items():
                assert key not in self.content['subdoc']
                self.content['subdoc'][key] = value
        # *** End of a subdocument (info)
        if m_info_end:
            assert 'subdoc' in self.content
            parent = self.content['subdoc']
            if self.discard_empty_fragments:
                # Check that the document is not empty
                if '_sentences' not in parent and \
                   '_paragraphs' not in parent:
                    # if the document had no content, discard it ...
                    self.lines += 1
                    return None
            self.lines += 1
            if self.textreconstructor:
                # create Text object
                text_obj = self.textreconstructor.reconstruct_text( parent )
                return text_obj
            else:
                return self.content
        # *** New paragraph
        if m_par_start:
            # Create new paragraph
            new_paragraph = {}
            if self.store_fragment_attributes:
                attribs = parse_tag_attributes( stripped_line )
                for key, value in attribs.items():
                    if key in new_paragraph.keys():
                       raise Exception("(!) Unexpected repeating attribute name in <p>: "+str(key))
                    new_paragraph[key] = value
            # Attach the paragraph
            parent = None
            if 'subdoc' in self.content:
                parent = self.content['subdoc']
            else:
                parent = self.content
            if '_paragraphs' not in parent:
                parent['_paragraphs'] = []
            parent['_paragraphs'].append( new_paragraph )
        # *** Paragraph's end
        if m_par_end:
            if self.discard_empty_fragments:
                # Check if the last paragraph was empty
                parent = None
                if 'subdoc' in self.content:
                    parent = self.content['subdoc']
                else:
                    parent = self.content
                if '_paragraphs' in parent:
                    assert len(parent['_paragraphs']) > 0
                    parent = parent['_paragraphs']
                    if parent:
                        # If there are no words nor sentences, remove 
                        # the empty paragraph
                        if ('_sentences' not in parent[-1] or \
                            len(parent[-1]['_sentences']) == 0) \
                            and \
                           ('_words' not in parent[-1] or \
                            len(parent[-1]['_words']) == 0):
                            parent.pop()
        # *** New sentence
        if m_s_start:
            # Create new sentence
            new_sentence = {}
            if self.store_fragment_attributes:
                attribs = parse_tag_attributes( stripped_line )
                for key, value in attribs.items():
                    if key in new_sentence.keys():
                       raise Exception("(!) Unexpected repeating attribute name in <p>: "+str(key))
                    new_sentence[key] = value
            # Attach the sentence
            parent = None
            if 'subdoc' in self.content:
                parent = self.content['subdoc']
            else:
                parent = self.content
            if '_paragraphs' in parent:
                assert len(parent['_paragraphs']) > 0
                parent = parent['_paragraphs'][-1]
            if '_sentences' not in parent:
                parent['_sentences'] = []
            parent['_sentences'].append( new_sentence )
        # *** Sentence end
        if m_s_end:
            if self.discard_empty_fragments:
                # Check if the last sentence was empty
                parent = None
                if 'subdoc' in self.content:
                    parent = self.content['subdoc']
                else:
                    parent = self.content
                if '_paragraphs' in parent:
                    assert len(parent['_paragraphs']) > 0
                    parent = parent['_paragraphs'][-1]
                if '_sentences' in parent:
                    assert len(parent['_sentences']) > 0
                    parent = parent['_sentences']
                    if parent:
                        # If there are no words, remove the empty sentence
                        if '_words' not in parent[-1] or \
                           len(parent[-1]['_words']) == 0:
                            parent.pop()
        # *** The glue tag: tokens from both side should be joined 
        if m_glue:
            self.last_was_glue = True
        # *** Text content + morph analysis inside sentence or paragraph
        elif len( stripped_line ) > 0 and '\t' in stripped_line:
            # Some sanity checks
            assert stripped_line.count('\t') >= 2, \
                ('(!) Unexpected number of tabs ({}) in '+\
                 'textual content line: {!r}').format(
                        stripped_line.count('\t'), 
                        stripped_line )
            # Add word
            items = stripped_line.split('\t')
            token = items[0]
            self._add_new_word_token( token )
        elif m_unk_tag:
            # *** Check for unknown tags
            tagname = m_unk_tag.group(1)
            tagname = tagname.lstrip('/')
            tagname = tagname.split()[0]
            if tagname not in ['g', 's', 'p', 'info', 'doc']:
                if not self.add_unknown_tags_to_words:
                    raise Exception('(!) Unexpected tag encountered: '+str(stripped_line))
                else:
                    # Add tag as word
                    self._add_new_word_token( stripped_line )
        self.lines += 1
        return None



    def _add_new_word_token( self, word_str: str ):
        '''Inserts given word_str into the document under reconstruction.
        
           Finds appropriate substructure (e.g. last paragraph or last 
           sentence) which is incomplete and adds word to the structure.
           Taking account of any glue markings added between the words.
        '''
        # Get the parent
        parent = None
        if 'subdoc' in self.content:
            parent = self.content['subdoc']
        else:
            parent = self.content
        if '_paragraphs' in parent:
            assert len(parent['_paragraphs']) > 0
            parent = parent['_paragraphs'][-1]
        if '_sentences' in parent:
            assert len(parent['_sentences']) > 0
            parent = parent['_sentences'][-1]
        if '_words' not in parent:
            # _original_words == words separated by 
            #                    whitespace
            parent['_original_words'] = []
            # _words == words morphologically analysed;
            #           these words can be tokens inside 
            #           _original_words
            parent['_words'] = []
        prev_words = parent['_words']
        prev_original_words = parent['_original_words']
        # Add given word
        prev_words.append( word_str )
        if self.last_was_glue:
            # Merge word to the previous one
            prev_original_words[-1] = prev_original_words[-1] + word_str
        else:
            # Add a new word to the list 
            prev_original_words.append( word_str )
        self.last_was_glue = False


# =================================================
#   Corpus iterators
# =================================================

def parse_enc2017_file_iterator( in_file, 
                                 encoding='utf-8', \
                                 focus_doc_ids=None, \
                                 focus_srcs=None, \
                                 focus_lang=None, \
                                 tokenization='preserve', \
                                 discard_empty_fragments=True, \
                                 store_fragment_attributes=True, \
                                 textreconstructor=None ):
    '''Opens an ENC 2017 corpus file (a prevert type file), reads 
       its content document by document, reconstructs Text objects 
       from the documents, and yields created Text objects one by 
       one.
       
       If tokenization=='preserve' (default), then created Text 
       objects will have layers preserving original segmentation:
       '_original_paragraphs', '_original_sentences', '_original_words'
       and '_original_word_chunks'.
       The layer '_original_word_chunks' contains words glued together
       with punctuation.
       If tokenization=='estnltk', then the created Text objects 
       will be tokenized with estnltk's default tools, and the original
       tokenization will be discarded.
       And if tokenization=='none', no tokenization will be added 
       to texts.
       
       Parameters
       ----------
       in_file: str
           Full name of etTenTen corpus file (name with path);
           
       encoding: str
           Encoding of in_file. Defaults to 'utf-8';
       
       focus_doc_ids: set of str
           Set of document id-s corresponding to the documents which 
           need to be extracted from the XML content of the file.
           If provided, then only documents with given id-s will be 
           parsed, and all other documents will be skipped.
           If None or empty, then all documents in the content will 
           be parsed.
           Important note: ids must be given as strings, not as 
           integers.
       
       focus_srcs: set of str
           Set of document src-s corresponding to subcorpora which 
           documents need to be extracted from the file.
           If provided, then only documents that have a src value from
           the set will be extracted, and all other documents will 
           be skipped.
           If None or empty, then all documents in the content will 
           be parsed.
       
       focus_lang: set of str
           Set of allowed document languages.
           If provided, then only documents that have a lang value from
           the set will be extracted, and all other documents will 
           be skipped. Note that if focus_lang is set, but the document
           does not have lang attribute, then the document will also be 
           skipped;
           If None or empty, then all documents in the content will 
           be parsed.
       
       tokenization: ['none', 'preserve', 'estnltk']
            Specifies if tokenization will be added to created Texts, 
            and if so, then how it will be added. 
            Three options:
            * 'none'     -- text   will   be   created  without  any 
                            tokenization layers;
            * 'preserve' -- original tokenization from XML files will 
                            be preserved in layers of the text; 
            * 'estnltk'  -- text's original tokenization will be 
                            overwritten by estnltk's tokenization;
           (default: 'preserve')
       
       discard_empty_fragments: boolean
           If set, then empty text fragments -- paragraphs and sentences --
           will be discarded.
           (default: True)
       
       store_fragment_attributes: boolean
           If set, then attributes in the XML tag of a paragraph or sentence 
           will be collected and added as attributes of the corresponding 
           layer in Text object.
           (default: True)
    '''
    assert not textreconstructor or isinstance(textreconstructor, ENC2017TextReconstructor)
    if textreconstructor:
        reconstructor = textreconstructor
    else:
        reconstructor = ENC2017TextReconstructor(tokenization=tokenization,\
                                                 layer_name_prefix='original_')
    xmlParser = PrevertXMLFileParser(
                   focus_ids=focus_doc_ids, \
                   focus_srcs=focus_srcs, \
                   focus_lang=focus_lang, \
                   discard_empty_fragments=discard_empty_fragments, \
                   store_fragment_attributes=store_fragment_attributes, \
                   textreconstructor=reconstructor )
    with open( in_file, mode='r', encoding=encoding ) as f:
        for line in f:
            result = xmlParser.parse_next_line( line )
            if result:
                # If the parser completed a document and created a 
                # Text object, yield it gracefully
                yield result


def parse_enc2017_file_content_iterator( content, 
                                         focus_doc_ids=None, \
                                         focus_srcs=None, \
                                         focus_lang=None, \
                                         tokenization='preserve', \
                                         discard_empty_fragments=True, \
                                         store_fragment_attributes=True,\
                                         textreconstructor=None ):
    '''Reads ENC 2017 corpus file's content, extracts documents 
       based on the XML annotations, reconstructs Text objects from 
       the documents, and yields created Text objects one by one.
       
       If tokenization=='preserve' (default), then created Text 
       objects will have layers preserving original segmentation:
       '_original_paragraphs', '_original_sentences', '_original_words'
       and '_original_word_chunks'.
       The layer '_original_word_chunks' contains words glued together
       with punctuation.
       If tokenization=='estnltk', then the created Text objects 
       will be tokenized with estnltk's default tools, and the original
       tokenization will be discarded.
       And if tokenization=='none', no tokenization will be added 
       to texts.
       
       Parameters
       ----------
       content: str
           ENC 2017 corpus file's content (or a subset of the content) 
           as a string.
       
       focus_doc_ids: set of str
           Set of document id-s corresponding to the documents which 
           need to be extracted from the XML content of the file.
           If provided, then only documents with given id-s will be 
           parsed, and all other documents will be skipped.
           If None or empty, then all documents in the content will 
           be parsed.
           Important note: ids must be given as strings, not as 
           integers.
       
       focus_srcs: set of str
           Set of document src-s corresponding to subcorpora which 
           documents need to be extracted from the file.
           If provided, then only documents that have a src value from
           the set will be extracted, and all other documents will 
           be skipped.
           If None or empty, then all documents in the content will 
           be parsed.
       
       focus_lang: set of str
           Set of allowed document languages.
           If provided, then only documents that have a lang value from
           the set will be extracted, and all other documents will 
           be skipped. Note that if focus_lang is set, but the document
           does not have lang attribute, then the document will also be 
           skipped;
           If None or empty, then all documents in the content will 
           be parsed.
       
       tokenization: ['none', 'preserve', 'estnltk']
            Specifies if tokenization will be added to created Texts, 
            and if so, then how it will be added. 
            Three options:
            * 'none'     -- text   will   be   created  without  any 
                            tokenization layers;
            * 'preserve' -- original tokenization from XML files will 
                            be preserved in layers of the text; 
            * 'estnltk'  -- text's original tokenization will be 
                            overwritten by estnltk's tokenization;
           (default: 'preserve')
       
       discard_empty_fragments: boolean
           If set, then empty text fragments -- paragraphs and sentences --
           will be discarded.
           (default: True)
       
       store_fragment_attributes: boolean
           If set, then attributes in the XML tag of a paragraph or sentence 
           will be collected and added as attributes of the corresponding 
           layer in Text object.
           (default: True)
       
       textreconstructor: ENC2017TextReconstructor
           If set, then overrides the default ENC2017TextReconstructor with the 
           given textreconstructor.
    '''
    assert isinstance(content, str)
    assert not textreconstructor or isinstance(textreconstructor, ENC2017TextReconstructor)
    if textreconstructor:
        reconstructor = textreconstructor
    else:
        reconstructor = ENC2017TextReconstructor(tokenization=tokenization,\
                                                 layer_name_prefix='original_')
    xmlParser = PrevertXMLFileParser(
                   focus_ids=focus_doc_ids, \
                   focus_srcs=focus_srcs, \
                   focus_lang=focus_lang, \
                   discard_empty_fragments=discard_empty_fragments, \
                   store_fragment_attributes=store_fragment_attributes, \
                   textreconstructor=reconstructor )
    # Process the content line by line
    for line in content.splitlines( keepends=True ):
        result = xmlParser.parse_next_line( line )
        if result:
            # If the parser completed a document and created a 
            # Text object, yield it gracefully
            yield result

