from estnltk.core import rel_path
from estnltk.taggers import TaggerTester
from estnltk.taggers import RobustDateNumberTagger

# test data created by estnltk/dev_documentation/testing/test_data_for_measurement_taggers.ipynb


def test_tagger():
    tagger = RobustDateNumberTagger(conflict_resolving_strategy='ALL')
    input_file = rel_path('tests/test_taggers/test_standard_taggers/robust_date_number_tagger_input.json')
    target_file = rel_path('tests/test_taggers/test_standard_taggers/robust_date_number_tagger_target.json')

    tester = TaggerTester(tagger, input_file, target_file).load()
    tester.run_tests()