#Standard Library Imports
import pdb
from pathlib import Path

#Installed Dependency Imports
import pytest

#Teatool Studio Imports
from tts_data_utils.multimission.eha import EhaContainer
from tts_data_utils.multimission.expected_lad import ExpectedLadContainer
from tts_utilities.logger import create_logger

#This Library Imports
from tts_dante.core.dante import Dante
from tts_dante.core.derive import Deriver, deriver_method
from tts_dante.derivers.eha import LadChanvalDeriver

logger = create_logger(f'dante.test.test_eha_derivations')
TEST_FILE_DIR = Path(__file__).parent.parent.joinpath('test_files/eha')


class DanteTester(Dante):
    def __init__(self, chanvals=None, expected_lad=None):
        super().__init__()
        self.init_data(EhaContainer, chanvals)
        self.init_data(ExpectedLadContainer, expected_lad, "expected eha lad")
        self.init_deriver(LadChanvalDeriver)

class TestEhaDerivers:
    def test_lad_chanval_deriver(self):
        chanvals = EhaContainer(csv_path=TEST_FILE_DIR.joinpath('lad_expected_vs_actual.csv'), cast_fields=True)
        expected_lad = ExpectedLadContainer(csv_path=TEST_FILE_DIR.joinpath('eha_autodispositions.csv'))
        dante = DanteTester(chanvals=chanvals, expected_lad=expected_lad)
        dante.derive_all()
        # OK, so why do we do this thing where we write actual and then read it right back in instead of 
        # checking the actual thing? This is a workaround. It has to do with the fact that diff will
        # differentiate between source and derived_values
        #
        # because this deriver changes the original container in place, the source/derived values will
        # not be the same for both that one and the one read in from CSV since that information is
        # flattened out in the CSV layer. So we read back in the actuals csv to get that same
        # flattening here since we're making it anyway for the benefit of being able to see what
        # has changed in git diffs when this test fails due to the diff changing.

        actual_lad_chanvals_output = dante.get_output_data('lad_chanvals.lad_chanvals')
        actual_lad_chanvals_output.to_csv(TEST_FILE_DIR.joinpath('actual_lad_chanvals_output.csv'))
        # actual_lad_chanvals_output.to_csv(TEST_FILE_DIR.joinpath('expected_lad_chanvals_output.csv'))

        #why set validate to false? This is work to go in data containers... this Dante dispo uses with_colums(), 
        #which removes and adds some columns before writing to CSV. So when we try to read it back in, it thinks
        #we have invalid data. But this is a small enough use case where we can just disable validation, and it should
        #be OK
        actual_lad_chanvals_output = ExpectedLadContainer(csv_path=TEST_FILE_DIR.joinpath('actual_lad_chanvals_output.csv'), cast_fields=True, validate=False)
        expected_lad_chanvals_output = ExpectedLadContainer(csv_path=TEST_FILE_DIR.joinpath('expected_lad_chanvals_output.csv'), cast_fields=True, validate=False)

        assert len(actual_lad_chanvals_output.diff(expected_lad_chanvals_output, ignore='history').eq('Same', False)) == 0, 'Diff does not match. Note that this is expected (for now) in python 3.6.8'
        assert len(actual_lad_chanvals_output.diff(expected_lad_chanvals_output)) == 914

