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

logger = create_logger(f'dante.eha')

class LadChanvalDeriver(Deriver):
    """
    Deriver for generating Latest Available Data (LAD) channel value comparisons.

    This class merges actual EHA channel values with a set of expected LAD definitions
    to create a comprehensive dataset showing what was expected versus what was
    actually received (or not received).
    """
    NAME = 'lad_chanvals'

    @deriver_method(['eha', 'expected eha lad'])
    def lad_chanvals(self, chanvals, expected_lad, time_type='scet'):
        """        
        Iterates through the expected LAD definitions and attempts to find the corresponding
        latest value in the provided actual channel values (`chanvals`). It populates
        'Actual Value' and 'Measurement Time' columns for each expected entry.

        Handles edge cases:
        - If no actual data is found for a channel, 'Actual Value' is set to 'Not Present'.
        - If multiple values are found (unexpectedly for a LAD set), 'Actual Value' is set to 'Ambiguous'.

        Args:
            chanvals (EhaContainer): The actual EHA channel data.
            expected_lad (ExpectedLadContainer or str): The expected LAD definitions or a path to a CSV file containing them.
            time_type (str, optional): The time field to use for 'Measurement Time' (e.g., 'scet', 'ert'). Defaults to 'scet'.

        Returns:
            DataContainer: A copy of the expected LAD container populated with actual values and times,
                           filtered to a specific set of relevant columns.
        """
        if not isinstance(expected_lad, ExpectedLadContainer):
            expected_lad = ExpectedLadContainer(csv_path=expected_lad, cast_fields=True)
        expected_and_actual_lad = expected_lad._copy()
        actual_lad = chanvals.lad()
        for channel in expected_and_actual_lad:
            this_value_actual_lad = actual_lad.eq('channelId', channel['Channel ID'])
            if len(this_value_actual_lad) == 0:
                channel['Actual Value'] = 'Not Present'
                channel['Measurement Time'] = 'NA'
            elif len(this_value_actual_lad) > 1:
                channel['Actual Value'] = 'Ambiguous'
                channel['Measurement Time'] = 'NA'
            else:
                channel['Actual Value'] = this_value_actual_lad[0][channel['Data Type']]
                channel['Measurement Time'] = this_value_actual_lad[0][time_type]

        return expected_and_actual_lad.with_cols([
                'Group',
                'Channel ID',
                'Display Name',
                'Expected Value',
                'Condition',
                'Tolerance',
                'Special Handling',
                'Actual Value',
                'Measurement Time',
                'disposition'
            ])