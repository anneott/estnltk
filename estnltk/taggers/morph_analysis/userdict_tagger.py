#
#   Makes user-specified post-corrections to morphological analyses.
#  Basically, rewrites automatically produced morphological analyses 
#  with user-specified ones.
# 
import copy
import csv
import io

from typing import MutableMapping

from estnltk.layer.layer import Annotation, Span, Layer
from estnltk.taggers import Retagger

from estnltk.taggers.morph_analysis.morf_common import ESTNLTK_MORPH_ATTRIBUTES
from estnltk.taggers.morph_analysis.morf_common import VABAMORF_ATTRIBUTES
from estnltk.taggers.morph_analysis.morf_common import NORMALIZED_TEXT
from estnltk.taggers.morph_analysis.morf_common import _postprocess_root

from estnltk.taggers.morph_analysis.morf_common import VABAMORF_POSTAGS
from estnltk.taggers.morph_analysis.morf_common import VABAMORF_NOUN_FORMS
from estnltk.taggers.morph_analysis.morf_common import VABAMORF_VERB_FORMS

# Value indicating unspecified field/value in the csv file
CSV_UNSPECIFIED_FIELD = '----------'


class UserDictTagger(Retagger):
    """Makes user-specified post-corrections to morphological analyses.
       This tagger can be applied after text has been morphologically analysed."""
    output_attributes = ESTNLTK_MORPH_ATTRIBUTES
    conf_param = ['depends_on', 'ignore_case', 'validate_vm_categories',
                  'autocorrect_root', '_dict', 'replace_missing_normalized_text_with_text']

    def __init__(self,
                 output_layer: str = 'morph_analysis',
                 ignore_case: bool = False,
                 validate_vm_categories: bool = True,
                 autocorrect_root: bool = True,
                 replace_missing_normalized_text_with_text: bool = False):
        """ Initialize UserDictTagger class.

        Parameters
        ----------
        output_layer: str (default: 'morph_analysis')
            Name of the morphological analysis layer that is to be changed;
        
        ignore_case: bool (default: False)
            If True, then case will be ignored when matching words in the text
            with words in the dictionary. Basically, all words added to the 
            dictionary will be converted to lowercase, and words in text will also 
            be converted to lowercase before the dictionary lookup;
        
        validate_vm_categories: bool (default: True)
            If True, then each analysis is checked for validity of partofspeech
            and form categories. Note that validation only checks if the respective 
            category values are valid category values for Vabamorf. But it does not
            check that the category values are also correctly combined (e.g. 
            partofspeech and form have been correctly combined);
        
        autocorrect_root: bool (default: True)
            If True, then dictionary entries for 'root_tokens' and 'lemma' will 
            be automatically generated and replaced, iff entries for 'root' and 
            'partofspeech' are given by the user. Note: this requires that when-
            ever 'root' has been specified by the user, 'partofspeech' must also 
            be specified (otherwise 'lemma' cannot be generated);
        
        replace_missing_normalized_text_with_text: bool (default: False)
            If True and the NORMALIZED_TEXT is missing from dictionary's record,
            then replace it by text. Otherwise, if the NORMALIZED_TEXT is missing
            from a record, then the value of NORMALIZED_TEXT will be None after
            overwriting.
        """
        self.output_layer = output_layer
        self.input_layers = [output_layer]
        self.depends_on   = self.input_layers
        
        self.ignore_case  = ignore_case
        self.validate_vm_categories = validate_vm_categories
        self.autocorrect_root       = autocorrect_root
        self.replace_missing_normalized_text_with_text = \
             replace_missing_normalized_text_with_text
        self._dict = {}



    def add_word(self, word, analysis_struct):
        """ Adds a word and its new morphological analysis to the user 
            dictionary.
            
            Note: if the user dictionary already contains entry for the word,
                  then the old entry will be overwritten with the new one;
                  
            Partial overwriting
            --------------------
            If  analysis_struct  is a dict, then its content will be used for 
            partial overwriting of the analysis in text: fields present in the 
            dict will be overwritten, and fields not present in the dict will 
            remain as they are.
            For instance, you can specify that only 'partofspeech' will be 
            changed, and other fields will remain as they are.
            The minimum requirement for the partial overwriting dict: it must 
            specify only one of the fields: 'root', 'ending', 'clitic', 'form', 
            'partofspeech';
            
            Complete overwriting
            --------------------
            If  analysis_struct  is a list, then its content will be used for 
            complete overwriting: word's analyses in the text will be completely
            replaced with the content of the list.
            Therefore, the list must contain at least one analysis dict (in case 
            of unambiguous word), or several dicts (in case of ambiguous word).
            Each dict must contain fields  'root', 'ending', 'clitic', 'form', 
            'partofspeech';
            
            Note: you should not specify manually 'root_tokens' and 'lemma', but 
            instead specify correct values for 'root', 'ending', and 'partofspeech', 
            and let the automagic to do the work (the flag 'autocorrect_root' must 
            be set for the automatic to happen!).
            
            Note: if validate_vm_categories is set, then partofspeech and form
            category names will be validated before accepting the entry (an 
            AssertionError will be thrown is validation fails).
            
        Parameters
        ----------
        word: str
            Word which entry is to be added to the user dictionary.
            If ignore_case is set, it will be converted to lowercase.
        
        analysis_struct: dict or list
            If analysis_struct is a dict, then it must contain at least one 
            of the keys 'root', 'ending', 'clitic', 'form', 'partofspeech',
            and the word's analyses in the text will be partially overwritten
            with the keys-values in the dict.
            If analysis_struct is a list (of dicts), then each of its dicts must 
            contain keys 'root', 'ending', 'clitic', 'form', 'partofspeech',
            and the word's analyses in the text will be completely overwritten
            with the dicts in the list.

        """
        assert isinstance(word, str)
        assert isinstance(analysis_struct, (dict, list))
        # Ignore case (if required)
        originalcase_word = word
        if self.ignore_case:
            word = word.lower()
        if isinstance(analysis_struct, dict):
            # validate attributes & attribute names
            assert len(analysis_struct.keys()) > 0
            has_any_attrib = \
                any([ attr in analysis_struct for attr in VABAMORF_ATTRIBUTES ])
            assert has_any_attrib, \
                    '(!) Entry '+str(analysis_struct)+' should contain at least one key '+\
                   'from the following: '+str(VABAMORF_ATTRIBUTES)
            # validate category names
            if self.validate_vm_categories:
                self.validate_morph_record_for_vm_categories(analysis_struct)
            self._dict[word] = {}
            self._dict[word]['analysis'] = \
                [ copy.deepcopy(analysis_struct) ]
            # Autocorrect root analysis: 
            #    generate cleaned root, root_tokens & lemma
            if self.autocorrect_root:
                if 'root' in self._dict[word]['analysis'][0]:
                    assert 'partofspeech' in self._dict[word]['analysis'][0], \
                        "(!) Please provide 'partofspeech' value in "+str(self._dict[word]['analysis'][0])+\
                        " to enable autocorrection of root / lemma."
                    postag = self._dict[word]['analysis'][0]['partofspeech']
                    root   = self._dict[word]['analysis'][0]['root']
                    root, root_tokens, lemma = _postprocess_root( root, postag )
                    self._dict[word]['analysis'][0]['lemma'] = lemma
                    self._dict[word]['analysis'][0]['root_tokens'] = root_tokens
                    self._dict[word]['analysis'][0]['root']  = root
            if self.replace_missing_normalized_text_with_text:
                if NORMALIZED_TEXT not in self._dict[word]['analysis'][0]:
                    self._dict[word]['analysis'][0][NORMALIZED_TEXT] = originalcase_word
            # Merge analyses: overwrite analysis fields that
            # are present in the dict, but preserve all other
            # fields
            self._dict[word]['merge'] = True
        elif isinstance(analysis_struct, list):
            assert len(analysis_struct) > 0
            # validate that all records are complete and well-formed
            for record in analysis_struct:
                assert isinstance(record, dict)
                # Check that the record has all VM attributes
                # ( a minimum set of attributes )
                missing = []
                for attr in VABAMORF_ATTRIBUTES:
                    if attr not in record:
                        missing.append(attr)
                assert not missing, \
                    '(!) Entry '+str(record)+' misses the following keys: '+str(missing)
                # Validate category names
                if self.validate_vm_categories:
                    self.validate_morph_record_for_vm_categories(record)
                # Autocorrect root analysis: 
                #    generate cleaned root, root_tokens & lemma
                if self.autocorrect_root:
                    if 'root' in record:
                        assert 'partofspeech' in record, \
                            "(!) Please provide 'partofspeech' value in "+str(record)+\
                            " to enable autocorrection of root / lemma."
                        postag = record['partofspeech']
                        root   = record['root']
                        root, root_tokens, lemma = _postprocess_root( root, postag )
                        record['lemma']       = lemma
                        record['root_tokens'] = root_tokens
                        record['root']        = root
                if self.replace_missing_normalized_text_with_text:
                    if NORMALIZED_TEXT not in record:
                        record[NORMALIZED_TEXT] = originalcase_word
            self._dict[word] = {}
            self._dict[word]['analysis'] = \
                copy.deepcopy(analysis_struct)
            # Overwrite analyses: delete all existing analyses,
            # and add new analyses from the dict
            self._dict[word]['merge'] = False



    def add_words_from_csv_file(self, filename, encoding='utf-8', \
                                dialect='excel-tab', 
                                allow_unspecified_fields=True, 
                                **fmtparams):
        ''' Loads words with their morphological analyses from the given 
            csv file, and inserts to the user dictionary.
            
            Note: any words already having entries in the user dictionary 
                  will have their old entries overwritten with the new 
                  ones;
            
            By default, assumes that csv file is in tab-separated-values 
            format (dialect='excel-tab') and in the encoding 'utf-8'.
            You can change the encoding via parameter encoding. And you
            can also provide other custom parameters ( from the parameters 
            listed in: 
            https://docs.python.org/3/library/csv.html#csv-fmt-params )
            if your input csv file has some other format.
            
            It is required that the first line of the file is the header,
            and uses the heading names 'root', 'ending', 'clitic', 'form', 
            'partofspeech', 'text'. This is required to determine in which 
            order the data needs to be loaded from the file.
            Each line following the heading specifies a single analysis for
            a word. The word itself must be under the column 'text'.
            Note that there can also be multiple lines for a single word:
            these are considered as different analysis variants of an 
            ambiguous word.
            
            Note: after analyses have been collected from the file, they
            will be inserted to the dictionary via the method add_word().
            
        Parameters
        ----------
        filename: str
            Path to the csv file which contains entries. The first line of 
            the file must specify order of fields 'root', 'ending', 'clitic', 
            'form', 'partofspeech', 'text'. Each line following the heading 
            must specify a single analysis for a word. The word itself must 
            be under the column 'text'.
        
        encoding: str (Default: 'utf-8')
            Encoding of the csv file.
        
        dialect: str (Default: 'excel-tab')
            Parameter dialect to be passed to the function csv.reader().
            See https://docs.python.org/3/library/csv.html#csv.reader
            for details.

        allow_unspecified_fields: bool (default: True)
            If True (default), then some of the fileds/values can be left
            unspecified in the csv file, which enables defining entries of 
            partial overwriting. An unspecified field/value is marked with 
            the constant CSV_UNSPECIFIED_FIELD. If an entry has at least 
            one unspecified field/value, then it is considered as a partial 
            overwriting entry, otherwise, it is considered as a complete 
            overwriting entry.

        fmtparams: 
            Optional keyword arguments to be passed to the function 
            csv.reader().
            See https://docs.python.org/3/library/csv.html#csv.reader
            for details.
        '''
        collected_analyses = {}
        with open(filename, 'r', newline='', encoding=encoding) as csvfile:
            fle_reader = csv.reader(csvfile, dialect=dialect, **fmtparams)
            header = next(fle_reader)
            # Validate that header specifies all the required attribute names
            missing = []
            for attr in VABAMORF_ATTRIBUTES + ('text',):
                if attr not in header:
                    missing.append(attr)
            assert not missing, \
                '(!) CSV file header misses the following key(s): '+str(missing)
            # Parse csv file
            # Collect and aggregate analyses
            for row in fle_reader:
                assert len(row) == len(header), '(!) Unexpected number of elements in a row: {!r}'.format(row)
                analysis_dict = {}
                word_text = None
                for kid, key in enumerate(header):
                    if key != 'text':
                        if key == NORMALIZED_TEXT and len(row[kid]) == 0:
                            #  if NORMALIZED_TEXT is empty, consider it as 
                            #  a value left unspecified and ignore it.
                            continue
                        analysis_dict[key] = row[kid]
                    else:
                        word_text = row[kid]
                assert word_text, \
                    "'(!) Value for 'text' not specified in line: "+str(row)
                assert len(word_text) > 0, \
                    "'(!) 'text' is empty string in line: "+str(row)
                # Manage unspecified fields (if required):
                if allow_unspecified_fields:
                    has_unspecified_fields = []
                    for k in analysis_dict.keys():
                        if analysis_dict[k] == CSV_UNSPECIFIED_FIELD:
                            has_unspecified_fields.append(k)
                    if len(has_unspecified_fields) > 0:
                        # Remove unspecified fields
                        for k in has_unspecified_fields:
                            del analysis_dict[k]
                        # Add partial overwriting entry
                        if word_text not in collected_analyses:
                            collected_analyses[word_text] = {}
                        # Check for conflicts:
                        if isinstance(collected_analyses[word_text], list):
                            raise Exception('(!) Conflicting partial and complete overwriting entries for word {!r}'.format(word_text))
                        collected_analyses[word_text] = analysis_dict
                    else:
                        # No unspecified fields
                        # Add complete overwriting entry
                        if word_text not in collected_analyses:
                            collected_analyses[word_text] = []
                        # Check for conflicts:
                        if isinstance(collected_analyses[word_text], dict):
                            raise Exception('(!) Conflicting partial and complete overwriting entries for word {!r}'.format(word_text))
                        collected_analyses[word_text].append(analysis_dict)
                else:
                    # Add complete overwriting entry
                    if word_text not in collected_analyses:
                        collected_analyses[word_text] = []
                    collected_analyses[word_text].append(analysis_dict)
                    #print(', '.join(row))
        # Rewrite all analyses into the user dict
        for word in collected_analyses.keys():
            self.add_word( word, collected_analyses[word] )


    def save_as_csv(self, filename, encoding='utf-8', \
                          dialect='excel-tab', 
                          allow_unspecified_fields=True, 
                          **fmtparams):
        ''' Saves entries of the current dictionary as a csv format file.
            Optionally, if the input filename is None, constructs and 
            returns a csv string that contains the entries.
            
            By default, assumes that csv file is in tab-separated-values 
            format (dialect='excel-tab') and in the encoding 'utf-8'.
            You can change the encoding via parameter encoding. And you
            can also provide other custom parameters ( from the parameters 
            listed in: 
            https://docs.python.org/3/library/csv.html#csv-fmt-params )
            if your input csv file has some other format.
            
            The first line of the csv file will be the header with the 
            heading names 'root', 'ending', 'clitic', 'form', 'partofspeech', 
            'text'. Each line following the heading specifies a single 
            analysis for a word. The word itself can be under the column 
            'text'. Note that there can also be multiple lines for a single 
            word: these are considered as different analysis variants of an 
            ambiguous word.
            If an entry contains value equal to CSV_UNSPECIFIED_FIELD, then
            it is considered as a partial overwriting entry.
            
        Parameters
        ----------
        filename: str
            Path to the csv file which needs to be written. 
            If None, then instead of writing entries into a file, entries
            will be formatted as a csv format string and returned by the
            method.
        
        encoding: str (Default: 'utf-8')
            Encoding of the csv file.
        
        dialect: str (Default: 'excel-tab')
            Parameter dialect to be passed to the function csv.writer().
            See https://docs.python.org/3/library/csv.html#csv.writer
            for details.

        allow_unspecified_fields: bool (default: True)
            If True (default), then some of the fileds/values can be left
            unspecified in the csv file, which enables defining entries of 
            partial overwriting. An unspecified field/value is marked with 
            the constant CSV_UNSPECIFIED_FIELD. If an entry has at least 
            one unspecified field/value, then it is considered as a partial 
            overwriting entry, otherwise, it is considered as a complete 
            overwriting entry.

        fmtparams: 
            Optional keyword arguments to be passed to the function 
            csv.writer().
            See https://docs.python.org/3/library/csv.html#csv.writer
            for details.
        '''
        # Analyse the dictionary
        has_normalized_text = False
        has_partial_overwriting_entry = False
        for word_text in self._dict.keys():
            if self._dict[word_text]['merge']:
                has_partial_overwriting_entry = True
            assert isinstance(self._dict[word_text]['analysis'], list)
            recs = self._dict[word_text]['analysis']
            for rec in recs:
                if NORMALIZED_TEXT in rec:
                    has_normalized_text = True
        # Sanity check
        if has_partial_overwriting_entry and not allow_unspecified_fields:
            raise Exception('(!) Conflicting settings: allow_unspecified_fields==False, '+\
                            'but the user dictionary contains at least one partial overwriting '+\
                            'entry. Unspecified fields must be allowed for writing partial '+\
                            'overwriting entries.' )
        header_fields = VABAMORF_ATTRIBUTES 
        if has_normalized_text:
            header_fields = (NORMALIZED_TEXT,) + header_fields
        header_fields = ('text',) + header_fields
        # Construct/write the output
        if filename != None:
            output_csv = open(filename, 'w', encoding=encoding, newline='')
        else:
            output_csv = io.StringIO()
        csv_writer = csv.writer(output_csv, dialect=dialect, **fmtparams)
        csv_writer.writerow( header_fields )
        for word_text in sorted(self._dict.keys()):
            assert isinstance(self._dict[word_text]['analysis'], list)
            recs = self._dict[word_text]['analysis']
            for rec in recs:
                values = []
                for h in header_fields:
                    if h == 'text':
                        values.append( word_text )
                    elif h == NORMALIZED_TEXT:
                        if h not in rec:
                            values.append( '' )
                        else:
                            values.append( rec[h] )
                    elif h not in rec:
                        values.append( CSV_UNSPECIFIED_FIELD )
                    else:
                        values.append( rec[h] )
                assert len(values) == len(header_fields)
                csv_writer.writerow( values )
        returnable = None
        if isinstance(output_csv, io.StringIO):
            returnable = output_csv.getvalue()
        # Close ( either file or StringIO )
        output_csv.close()
        assert output_csv.closed
        return returnable


    def _change_layer(self, raw_text: str, layers: MutableMapping[str, Layer], status: dict = None) -> None:
        """Retags the morphological analyses layer, providing dictionary-
           based corrections to it.
           More technically: replaces existing analyses of the layer 
           'morph_analysis' with analyses from the user dictionary. 
           Dictionary lookup is made for a normalized_texts: if word's 
           analysis has a normalized_text which matches a word in 
           user dictionary, then word's analyses will be overwritten. 
           If ignore_case is switched on, then the lookup is also 
           case-insensitive.

           Parameters
           ----------
           raw_text: str
              Text string corresponding to the text which annotation
              layers will be corrected;
           layers: MutableMapping[str, Layer]
              Layers of the raw_text. Contains mappings from the name 
              of the layer to the Layer object. The mapping must 
              contain morph_analysis and words layers. 
              The morph_analysis layer will be retagged;
           status: dict
              This can be used to store metadata on layer retagging.
        """
        assert self.output_layer in layers
        # Take attributes from the input layer
        current_attributes = layers[self.output_layer].attributes
        # --------------------------------------------
        #   Rewrite spans according to the dict
        # --------------------------------------------
        morph_span_id = 0
        morph_spans = layers[self.output_layer].spans
        attribute_names = layers[self.output_layer].attributes
        while morph_span_id < len(morph_spans):
            # 1) Get morph records
            records = [span.to_record() for span in morph_spans[morph_span_id].annotations]
            overwrite_records = []
            records_merged = False
            # 2) Check morph records
            for rid, rec in enumerate( records ):
                assert NORMALIZED_TEXT in rec, \
                       '(!) Record {!r} is missing the attribute {!r}'.format(rec, NORMALIZED_TEXT)
                word_text = rec[NORMALIZED_TEXT]
                if word_text is None:
                    # If normalized_text is None, fall back to the morph_span.text
                    word_text = morph_spans[morph_span_id].text
                # Check the dictionary
                if self.ignore_case:
                    word_text = word_text.lower()
                if word_text in self._dict:
                    # 2) If the word is inside user dictionary
                    if self._dict[word_text]['merge']:
                        # Overwrite keys in dict, keep all other
                        # keys-values as they were before
                        merge_rec = self._dict[word_text]['analysis']
                        assert isinstance(merge_rec, list) and len(merge_rec) == 1
                        for key in merge_rec[0].keys():
                            rec[key] = merge_rec[0][key]
                        records_merged = True
                    else:
                        assert isinstance(self._dict[word_text]['analysis'], list)
                        overwrite_records = self._dict[word_text]['analysis']

            # If there are overwrite records, then overwrite the old records completely
            if records_merged or overwrite_records:
                records = overwrite_records if overwrite_records else records
                
                # 2.3) Create a new Span
                span = Span(morph_spans[morph_span_id].base_span, layer=layers[self.output_layer])

                # 2.4) Populate it with new records
                for rec in records:
                    attributes = {attr: rec.get(attr) for attr in attribute_names}
                    span.add_annotation( Annotation(span, **attributes) )

                # 2.5) Overwrite the old span
                morph_spans[morph_span_id] = span

            # Advance in the old "morph_analysis" layer
            morph_span_id += 1



    def validate_morph_record_for_vm_categories(self, morph_dict):
        """Validates given dictionary containing single morphological 
        analysis for correctness of Vabamorf's categories. 
        Note that validation only checks if the respective category 
        values are valid category values for Vabamorf, e.g. checks that 
        partofspeech does not have illegal value 'W'. 
        But the validation does not check that the category values are 
        also correctly combined (e.g. partofspeech and form have been 
        correctly combined).
        If one of the validations fails, then a ValueError will be 
        risen.
        
        Parameters
        ----------
        morph_dict: dict
            Dict object with morphological analyses of a word. Should 
            contain keys 'partofspeech' and 'form'.
        """
        assert isinstance(morph_dict, dict)
        for key, val in morph_dict.items():
            if key == 'partofspeech':
                if val not in VABAMORF_POSTAGS:
                    raise ValueError( "(!) Unexpected 'partofspeech':'"+str(val)+"'. "+\
                                      "Proper value should be one of the following: "+str(VABAMORF_POSTAGS) )
            if key == 'form':
                if len(val) > 0:
                    vals = val.split()
                    for v in vals:
                        if v not in VABAMORF_NOUN_FORMS and v not in VABAMORF_VERB_FORMS:
                            raise ValueError( "(!) Unexpected 'form':'"+str(val)+"'. "+\
                                              "Proper values should be from the following list: "+\
                                              str( VABAMORF_NOUN_FORMS + VABAMORF_VERB_FORMS ) )

