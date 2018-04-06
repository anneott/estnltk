#
#  Script for converting KoondKorpus XML TEI files to EstNTLK JSON format files.
#  Ported from the version 1.4.1.1:
#    https://github.com/estnltk/estnltk/blob/1.4.1.1/estnltk/examples/convert_koondkorpus.py
#    ( with modifications )
# 

import os
import os.path
import argparse
import logging

from datetime import datetime
from datetime import timedelta

from estnltk.corpus_processing.parse_koondkorpus import get_div_target
from estnltk.corpus_processing.parse_koondkorpus import parse_tei_corpus

from estnltk.converters import export_json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('koondkonverter')

output_ext = 'json'    # extension of output files

def process(start_dir, out_dir, encoding='utf-8', \
            preserve_tokenization=False, \
            create_empty_docs=True):
    """Traverses recursively start_dir to find XML TEI documents,
       converts found documents to EstNLTK Text objects, and saves 
       as JSON files (into the out_dir).
    
    Parameters
    ----------
    start_dir: str
        The root directory which is recursively traversed to find 
        XML files;
    out_dir: str
        The directory where results (EstNLTK Texts in JSON format)
        are to be saved;
    encoding: str
        Encoding of the XML files. (default: 'utf-8')
    preserve_tokenization: boolean
        If True, then the created documents will have layers 'words', 
        'sentences', 'paragraphs', which follow the original 
        segmentation in the XML file. 
        (In the XML, sentences are between <s> and </s> and paragraphs 
        are between <p> and </p>);
        Otherwise, the documents are created without adding layers 
        'words', 'sentences', 'paragraphs';
        (default: False)
    create_empty_docs: boolean
        If True, then documents are also created if there is no textual 
        content, but only metadata content.
        Note: an empty document may be a captioned table or a figure, 
        which content has been removed from the XML file. Depending on 
        the goals of the analysis, the caption may still be useful, 
        so, by default, empty documents are preserved;
        (default: True)
    """
    xml_count  = 0
    json_count = 0
    startTime = datetime.now()
    no_documents_created = []
    for dirpath, dirnames, filenames in os.walk(start_dir):
        if len(dirnames) > 0 or len(filenames) == 0 or 'bin' in dirpath:
            continue
        for fnm in filenames:
            full_fnm = os.path.join(dirpath, fnm)
            out_prefix = os.path.join(out_dir, fnm)
            target = get_div_target(full_fnm)
            if os.path.exists(out_prefix + '_0.'+output_ext):
                logger.info('Skipping file {0}, because it seems to be already processed'.format(full_fnm))
                continue
            logger.info('Processing file {0} with target {1}'.format(full_fnm, target))
            docs = []
            docs = parse_tei_corpus(full_fnm, target=[target], encoding=encoding, \
                                    preserve_tokenization=preserve_tokenization, \
                                    record_xml_filename=True)
            xml_count += 1
            empty_docs = []
            for doc_id, doc in enumerate(docs):
                out_fnm = '{0}_{1}.{2}'.format(out_prefix, doc_id, output_ext)
                logger.info('Writing document {0}'.format(out_fnm))
                if not create_empty_docs and len(doc.text) == 0:
                   # Skip creating an empty document
                   continue
                if len(doc.text) == 0:
                   empty_docs.append(out_fnm)
                export_json(doc, file = out_fnm)
                json_count += 1
            if empty_docs:
                logger.warn('Warning: empty documents created for {0}: {1}'.format(fnm, empty_docs))
            elif not docs:
                logger.warn('Warning: no documents created for {0}'.format(fnm))
                no_documents_created.append(fnm)
    if no_documents_created:
        logger.warn('No documents created for XML files: {0}'.format(no_documents_created))
    logger.info(' Total {0} XML files processed '.format(xml_count))
    logger.info(' Total {0} JSON files created '.format(json_count))
    time_diff = datetime.now() - startTime
    logger.info(' Total processing time: {}'.format(time_diff))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=
       "Converts Koondkorpus XML TEI files to EstNLTK JSON files."
    )
    parser.add_argument('startdir', type=str, help='The path of the downloaded and extracted koondkorpus files')
    parser.add_argument('outdir', type=str, help='The directory to store output results')
    parser.add_argument('-e', '--encoding', type=str, default='utf-8', \
                        help='Encoding of the TEI XML files (Default: "utf-8").')
    parser.add_argument('-p', '--preserve_tokenization', dest='preserve_tokenization', default=False, action='store_true', help="If set, then the created documents will have layers 'words', 'sentences', 'paragraphs', which follow the original segmentation in the XML file (sentences between <s> and </s> tags, paragraphs between <p> and </p> tags). Otherwise, the documents are created without adding layers 'words', 'sentences', and 'paragraphs'.")
    args = parser.parse_args()

    process(args.startdir, args.outdir, args.encoding, args.preserve_tokenization)