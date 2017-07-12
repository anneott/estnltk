from lxml import etree
from lxml.builder import ElementMaker
from estnltk import Text


def export_TCF(t: Text, file:str=None):
    '''
    Export Text to TCF XML format for
    https://weblicht.sfs.uni-tuebingen.de/weblicht/
    
    As a side-effect equips Text object with token layer.

    If file is not None, saves the result in file.
    Returns str
    '''

    token_ids = {word:'t'+str(i) for i, word in enumerate(t.words)}
    
    text_tree = etree.Element('D-Spin', xmlns="http://www.dspin.de/data", version="0.4")
    doc = etree.ElementTree(text_tree)
    
    etree.SubElement(text_tree, 'MetaData', xmlns="http://www.dspin.de/data/metadata")
    
    etree.SubElement(text_tree, 'TextCorpus', xmlns="http://www.dspin.de/data/textcorpus", lang="ee")
    
    etree.SubElement(text_tree[1], 'text').text = t.text
    
    
    E = ElementMaker(namespace='http://www.dspin.de/data/textcorpus',
                   nsmap={'tc':'http://www.dspin.de/data/textcorpus'})
    
    tokens = E('tokens')
    for word in t.words:
        tokens.append(E('token', word.text,  {'ID':token_ids[word], 'start':str(word.start), 'end':str(word.end)}))
    text_tree[1].append(tokens)
    
    sentences = E('sentences')
    for i, sentence in enumerate(t.sentences):
        token_IDs = ' '.join((token_ids[word] for word in sentence))
        sentences.append(E('sentence',  {'ID':'s'+str(i), 'tokenIDs':token_IDs}))
    text_tree[1].append(sentences)
    
    lemmas = E('lemmas')
    for analysis in t.morf_analysis:
        token_id = token_ids[analysis.words]
        for a in analysis:
            # kas nii on õige toimida mitmese märgendiga? (' '.join...)
            lemmas.append(E('lemma', a.lemma, {'ID':token_id.replace('t', 'l'),'tokenIDs':token_id}))
    text_tree[1].append(lemmas)
    
    postags = E('POStags', {'tagset':''})
    for analysis in t.morf_analysis:
        token_id = token_ids[analysis.words]
        for a in analysis:
            # kas nii on õige toimida mitmese märgendiga? (' '.join...)
            postags.append(E('tag', a.partofspeech, {'tokenIDs':token_id}))
    text_tree[1].append(postags)
    
    morphology = E('morphology')
    for analysis in t.morf_analysis:
        token_id = token_ids[analysis.words]
        for a in analysis:
            # kas nii on õige toimida mitmese märgendiga?
            features = E('fs')
            features.append(E('f', a.form, {'name':'form'}))
            features.append(E('f', a.root, {'name':'root'}))
            features.append(E('f', ' '.join(a.root_tokens), {'name':'root_tokens'}))
            features.append(E('f', a.ending, {'name':'ending'}))
            features.append(E('f', a.clitic, {'name':'clitic'}))
            tag = E('tag', features)
            morphology.append(E('analysis', tag, {'tokenIDs':token_id}))
    text_tree[1].append(morphology)
    
    if file is not None:
        doc.write(file, xml_declaration=True, encoding='UTF-8', pretty_print=True)
    return etree.tostring(text_tree, encoding='unicode', pretty_print=True)
