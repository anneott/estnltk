from estnltk import Text
from estnltk.corpus_processing.parse_koondkorpus import reconstruct_text
from estnltk.taggers.text_segmentation.whitespace_tokens_tagger import WhiteSpaceTokensTagger



def test_reconstruct_text_detached_layers():
    # Tests that the text and its layers can be reconstructed based on a dictionary representation
    # Test the situation when reconstructed layers are detached from each other
    # ( this kind of reconstruction is used in importing texts from koondkorpus XML files )
    tokenizer = WhiteSpaceTokensTagger()
    # dict representation of the text
    test_text_dict = { 'paragraphs': [ {'sentences':['Millist hinda oleme nõus maksma enese täiustamise eest?']}, \
                                       {'sentences':['Inimestel on palju eetilisi muresid, mis seostuvad vaimset '+\
                                        'võimekust parandavate ravimite või seadmetega, kuid tõenäoliselt haihtuvad '+\
                                        'need hetkel, mil turule ilmub esimene selline läbimurdeline vahend, tõdeb '+\
                                        'Oxfordi Ülikooli filosoof Anders Sandberg intervjuus Arko Oleskile.']}, \
                                       {'sentences':['REKLAAM']},\
                                       {'sentences':['Kas olete näinud filmi «Kõrvalnähud» («Limitless»), kus peategelane '+\
                                        'hakkab kasutama ravimit, mis tema vaimseid võimeid tohutult parandab, kuid jääb '+\
                                        'sellest sõltuvusse...']},\
                                       {'sentences':['Oo, jaa.', 'Mulle meeldis see väga.']},\
                                       {'sentences':['Tõesti?']},\
                                     ] }
    # Reconstruct the text
    wstokenizer = WhiteSpaceTokensTagger()
    text, tokenization_layers = reconstruct_text(test_text_dict, \
                                                 tokens_tagger=wstokenizer, \
                                                 use_enveloping_layers=False )
    
    # Make assertions #1
    expected_text = 'Millist hinda oleme nõus maksma enese täiustamise eest?\n\n'+\
                    'Inimestel on palju eetilisi muresid, mis seostuvad vaimset võimekust parandavate ravimite või seadmetega, kuid tõenäoliselt haihtuvad need hetkel, mil turule ilmub esimene selline läbimurdeline vahend, tõdeb Oxfordi Ülikooli filosoof Anders Sandberg intervjuus Arko Oleskile.\n\n'+\
                    'REKLAAM\n\n'+\
                    'Kas olete näinud filmi «Kõrvalnähud» («Limitless»), kus peategelane hakkab kasutama ravimit, mis tema vaimseid võimeid tohutult parandab, kuid jääb sellest sõltuvusse...\n\n'+\
                    'Oo, jaa.\n'+'Mulle meeldis see väga.\n\n'+\
                    'Tõesti?'
    assert text.text == expected_text
    assert any([layer.name=='words' for layer in tokenization_layers])
    assert any([layer.name=='sentences' for layer in tokenization_layers])
    assert any([layer.name=='paragraphs' for layer in tokenization_layers])
    
    # Attach layers
    for layer in tokenization_layers:
        text[layer.name] = layer
    words      = [layer for layer in tokenization_layers if layer.name=='words'][0]
    sentences  = [layer for layer in tokenization_layers if layer.name=='sentences'][0]
    paragraphs = [layer for layer in tokenization_layers if layer.name=='paragraphs'][0]
    # Make assertions #2
    expected_words = ['Millist', 'hinda', 'oleme', 'nõus', 'maksma', 'enese', 'täiustamise', 'eest?', \
                       'Inimestel', 'on', 'palju', 'eetilisi', 'muresid,', 'mis', 'seostuvad', 'vaimset', \
                       'võimekust', 'parandavate', 'ravimite', 'või', 'seadmetega,', 'kuid', 'tõenäoliselt', \
                       'haihtuvad', 'need', 'hetkel,', 'mil', 'turule', 'ilmub', 'esimene', 'selline', \
                       'läbimurdeline', 'vahend,', 'tõdeb', 'Oxfordi', 'Ülikooli', 'filosoof', 'Anders', \
                       'Sandberg', 'intervjuus', 'Arko', 'Oleskile.', 'REKLAAM', 'Kas', 'olete', 'näinud', \
                       'filmi', '«Kõrvalnähud»', '(«Limitless»),', 'kus', 'peategelane', 'hakkab', 'kasutama',\
                       'ravimit,', 'mis', 'tema', 'vaimseid', 'võimeid', 'tohutult', 'parandab,', 'kuid', 'jääb',\
                       'sellest', 'sõltuvusse...', 'Oo,', 'jaa.', 'Mulle', 'meeldis', 'see', 'väga.', 'Tõesti?']
    assert words.text == expected_words
    expected_sentences = ['Millist hinda oleme nõus maksma enese täiustamise eest?', \
                          'Inimestel on palju eetilisi muresid, mis seostuvad vaimset võimekust parandavate '+\
                          'ravimite või seadmetega, kuid tõenäoliselt haihtuvad need hetkel, mil turule ilmub '+\
                          'esimene selline läbimurdeline vahend, tõdeb Oxfordi Ülikooli filosoof Anders Sandberg '+\
                          'intervjuus Arko Oleskile.', 'REKLAAM', 'Kas olete näinud filmi «Kõrvalnähud» («Limitless»), '+\
                          'kus peategelane hakkab kasutama ravimit, mis tema vaimseid võimeid tohutult parandab, '+\
                          'kuid jääb sellest sõltuvusse...', 'Oo, jaa.', 'Mulle meeldis see väga.', 'Tõesti?']
    assert sentences.text == expected_sentences
    expected_paragraphs = ['Millist hinda oleme nõus maksma enese täiustamise eest?', \
                           'Inimestel on palju eetilisi muresid, mis seostuvad vaimset võimekust parandavate '+\
                          'ravimite või seadmetega, kuid tõenäoliselt haihtuvad need hetkel, mil turule ilmub '+\
                          'esimene selline läbimurdeline vahend, tõdeb Oxfordi Ülikooli filosoof Anders Sandberg '+\
                          'intervjuus Arko Oleskile.', 'REKLAAM', \
                          'Kas olete näinud filmi «Kõrvalnähud» («Limitless»), '+\
                          'kus peategelane hakkab kasutama ravimit, mis tema vaimseid võimeid tohutult parandab, '+\
                          'kuid jääb sellest sõltuvusse...', 'Oo, jaa.\nMulle meeldis see väga.', 'Tõesti?']
    assert paragraphs.text == expected_paragraphs




def test_reconstruct_text_enveloping_layers():
    # Tests that the text and its layers can be reconstructed based on a dictionary representation
    # Test the situation when reconstructed layers are connected via enveloping
    # ( this kind of reconstruction is used in importing texts from koondkorpus XML files )
    tokenizer = WhiteSpaceTokensTagger()
    # dict representation of the text
    test_text_dict = { 'paragraphs': [ {'sentences':['Millist hinda oleme nõus maksma enese täiustamise eest?']}, \
                                       {'sentences':['Inimestel on palju eetilisi muresid, mis seostuvad vaimset '+\
                                        'võimekust parandavate ravimite või seadmetega, kuid tõenäoliselt haihtuvad '+\
                                        'need hetkel, mil turule ilmub esimene selline läbimurdeline vahend, tõdeb '+\
                                        'Oxfordi Ülikooli filosoof Anders Sandberg intervjuus Arko Oleskile.']}, \
                                       {'sentences':['REKLAAM']},\
                                       {'sentences':['Kas olete näinud filmi «Kõrvalnähud» («Limitless»), kus peategelane '+\
                                        'hakkab kasutama ravimit, mis tema vaimseid võimeid tohutult parandab, kuid jääb '+\
                                        'sellest sõltuvusse...']},\
                                       {'sentences':['Oo, jaa.', 'Mulle meeldis see väga.']},\
                                       {'sentences':['Tõesti?']},\
                                     ] }
    # Reconstruct the text
    wstokenizer = WhiteSpaceTokensTagger()
    text, tokenization_layers = reconstruct_text(test_text_dict, \
                                                 tokens_tagger=wstokenizer, \
                                                 use_enveloping_layers=True )
    assert any([layer.name=='words' for layer in tokenization_layers])
    assert any([layer.name=='sentences' for layer in tokenization_layers])
    assert any([layer.name=='paragraphs' for layer in tokenization_layers])
    
    # Attach layers
    for layer in tokenization_layers:
        text[layer.name] = layer
    words      = [layer for layer in tokenization_layers if layer.name=='words'][0]
    sentences  = [layer for layer in tokenization_layers if layer.name=='sentences'][0]
    paragraphs = [layer for layer in tokenization_layers if layer.name=='paragraphs'][0]
    
    # Test relations: paragraphs
    assert text.paragraphs[0].sentences.text == ['Millist', 'hinda', 'oleme', 'nõus', 'maksma', 'enese', 'täiustamise', 'eest?']
    assert text.paragraphs[4].sentences.text == ['Oo,', 'jaa.', 'Mulle', 'meeldis', 'see', 'väga.']

    # Test relations: sentences
    assert text.sentences[1].text == ['Inimestel', 'on', 'palju', 'eetilisi', 'muresid,', 'mis', 'seostuvad', 'vaimset', 'võimekust', 'parandavate', 'ravimite', 'või', 'seadmetega,', 'kuid', 'tõenäoliselt', 'haihtuvad', 'need', 'hetkel,', 'mil', 'turule', 'ilmub', 'esimene', 'selline', 'läbimurdeline', 'vahend,', 'tõdeb', 'Oxfordi', 'Ülikooli', 'filosoof', 'Anders', 'Sandberg', 'intervjuus', 'Arko', 'Oleskile.']
    assert text.sentences[2].text == ['REKLAAM']
    
    # Test relations: words
    assert text.sentences[3].words[4:6].text == ['«Kõrvalnähud»', '(«Limitless»),']
    assert text.sentences[5].words[0:3].text == ['Mulle', 'meeldis', 'see']
    assert text.words[29:33].text == ['esimene', 'selline', 'läbimurdeline', 'vahend,']

