#Standard Library Imports
import pdb
from pathlib import Path

#Installed Dependency Imports
# None

#Teatool Studio Imports
from tts_data_utils.multimission.eha import EhaContainer
from tts_data_utils.multimission.expected_lad import ExpectedLadContainer
from tts_utilities.logger import create_logger

#This Library Imports
from tts_dante.core.derive import Deriver, deriver_method

logger = create_logger(__file__)

class EvrGapDeriver(Deriver):
    """
    Deriver for generating Latest Available Data (LAD) channel value comparisons.

    This class merges actual EHA channel values with a set of expected LAD definitions
    to create a comprehensive dataset showing what was expected versus what was
    actually received (or not received).
    """
    NAME = 'evr_gaps'

    @deriver_method(['evrs'])
    def evr_gaps(self, evrs):
        return evrs.gaps()