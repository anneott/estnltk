from estnltk.text import Text
from estnltk.taggers.morph_analysis.vm_corpus_tagger import VabamorfCorpusTagger

from estnltk.tests.test_morph.test_cb_disambiguator import count_analyses


def test_vm_corpus_tagger_input_structures():
    import pytest
    #
    #  Tests the vm_corpus_tagger works on different input structures
    #
    vm_corpus_tagger = VabamorfCorpusTagger()
    #
    #   TestCase X : an empty list
    #
    docsy = []
    vm_corpus_tagger.tag( docsy )
    #
    #   TestCase Y : a Text as input gives AssertionError
    #        ( a collection of Text-s is required )
    #
    # Giving Text as an input gives AssertionError: 
    #   a list of Texts is expected
    text = Text('Tahtis kulda. Aga sai kasside kulla.')
    with pytest.raises(AssertionError) as e1:
        vm_corpus_tagger.tag( text )
    #
    #   TestCase Z : if some of the required 
    #       layers are missing raises Exception
    #
    text = Text('Tahtis kulda. Aga sai kasside kulla.')
    with pytest.raises(Exception) as ex1:
        vm_corpus_tagger.tag( [text] )


def test_vm_corpus_tagger_with_cb_predisambiguation():
    #
    #  Tests corpus-based pre-disambiguation
    #
    #
    # Case 1: don't use VM disambiguation
    #
    vm_corpus_tagger = VabamorfCorpusTagger(use_predisambiguation=True,
                                            use_vabamorf_disambiguator=False,
                                            use_postdisambiguation=False)
    docs = [ Text('Perekonnanimi oli Nõmm.'), \
             Text('Kuidas seda hääldada: Nõmmil või Nõmmel?') ]
    for doc in docs:
        doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(docs)
    # print( count_analyses(docs) )
    assert count_analyses(docs) == [16, 3, 13]
    #
    # Case 2: use VM disambiguation
    #
    vm_corpus_tagger = VabamorfCorpusTagger(use_predisambiguation=True,
                                            use_vabamorf_disambiguator=True,
                                            use_postdisambiguation=False)
    docs = [ Text('Perekonnanimi oli Nõmm.'), \
             Text('Kuidas seda hääldada: Nõmmil või Nõmmel?') ]
    for doc in docs:
        doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(docs)
    assert count_analyses(docs) == [12, 3, 9]


def test_vm_corpus_tagger_with_cb_postdisambiguation():
    #
    #  Tests corpus-based post-disambiguation
    #
    #
    #  Case 0: results without VM disambiguation and post-disambiguation
    #
    vm_corpus_tagger = VabamorfCorpusTagger(use_vabamorf_disambiguator=False,
                                            use_postdisambiguation=False)
    docs = [Text('Esimesele kohale tuleb Jänes, kuigi tema punktide summa pole kõrgeim.'),\
            Text('Lõpparvestuses läks Konnale esimene koht. Teine koht seekord Jänesele. Uus võistlus toimub 2. mail.'), \
            Text('Konn paistis silma suurima punktide summaga. Uue võistluse toimumisajaks on 2. mai.'),
            Text('Kordame: summat, summat, summat.'),]
    for doc in docs:
        doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(docs)
    assert count_analyses(docs) == [71, 4, 67]
    #
    #  Case 1: results without corpus-based post-disambiguation
    #
    vm_corpus_tagger = VabamorfCorpusTagger(use_vabamorf_disambiguator=True,
                                            use_postdisambiguation=False)
    docs = [Text('Esimesele kohale tuleb Jänes, kuigi tema punktide summa pole kõrgeim.'),\
            Text('Lõpparvestuses läks Konnale esimene koht. Teine koht seekord Jänesele. Uus võistlus toimub 2. mail.'), \
            Text('Konn paistis silma suurima punktide summaga. Uue võistluse toimumisajaks on 2. mai.'),
            Text('Kordame: summat, summat, summat.'),]
    for doc in docs:
        doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(docs)
    assert count_analyses(docs) == [57, 4, 53]
    #
    #  Case 2: results with corpus-based post-disambiguation
    #          (one-level input structure)
    #
    vm_corpus_tagger = VabamorfCorpusTagger(use_vabamorf_disambiguator=True,
                                            use_postdisambiguation=True)
    docs = [Text('Esimesele kohale tuleb Jänes, kuigi tema punktide summa pole kõrgeim.'),\
            Text('Lõpparvestuses läks Konnale esimene koht. Teine koht seekord Jänesele. Uus võistlus toimub 2. mail.'), \
            Text('Konn paistis silma suurima punktide summaga. Uue võistluse toimumisajaks on 2. mai.'),
            Text('Kordame: summat, summat, summat.'),]
    for doc in docs:
        doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(docs)
    assert count_analyses(docs) == [54, 4, 50]
    #
    #  Case 3: results with corpus-based post-disambiguation
    #          (two-level input structure)
    #
    corpus = [[Text('Esimesele kohale tuleb Jänes, kuigi tema punktide summa pole kõrgeim.'),\
               Text('Lõpparvestuses läks Konnale esimene koht. Teine koht seekord Jänesele. Uus võistlus toimub 2. mail.')], \
              [Text('Konn paistis silma suurima punktide summaga. Uue võistluse toimumisajaks on 2. mai.'),
               Text('Kordame: summat, summat, summat.')],]
    for sub_docs in corpus:
        for doc in sub_docs:
            doc.tag_layer(['compound_tokens', 'words', 'sentences'])
    vm_corpus_tagger.tag(corpus)
    # ! Results should be as good as in case of one level structure
    assert count_analyses(corpus) == [54, 4, 50]



def test_vm_corpus_tagger_with_changed_layer_names():
    #
    #  Tests that VabamorfCorpusTagger can operate on differently named layers
    #
    # 1) Initialize taggers with custom names 
    from estnltk.taggers import CompoundTokenTagger
    from estnltk.taggers import WordTagger
    from estnltk.taggers import SentenceTokenizer
    cp_tagger = CompoundTokenTagger(output_layer='my_compounds')
    word_tagger = WordTagger( input_compound_tokens_layer='my_compounds',
                              output_layer='my_words' )
    sentence_tokenizer = SentenceTokenizer( 
                              input_compound_tokens_layer='my_compounds',
                              input_words_layer='my_words',
                              output_layer='my_sentences' )
    vm_corpus_tagger = VabamorfCorpusTagger(morph_analysis_layer='my_morph',
                                            input_words_layer='my_words',
                                            input_sentences_layer='my_sentences',
                                            input_compound_tokens_layer='my_compounds')
    # 2) Tag Texts with customly named layers
    docs = [ Text('Perekonnanimi oli Nõmm.'), \
             Text('Kuidas seda hääldada: Nõmmil või Nõmmel?') ]
    for doc in docs:
        doc.tag_layer(['tokens'])
        cp_tagger.tag(doc)
        word_tagger.tag(doc)
        sentence_tokenizer.tag(doc)
    vm_corpus_tagger.tag(docs)
    # 3) Validate that morph analysis has been added
    for doc in docs:
        assert 'my_morph' in doc.layers.keys()
