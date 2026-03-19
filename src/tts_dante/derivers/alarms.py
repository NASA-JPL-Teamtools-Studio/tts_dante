#Standard Library Imports
import pdb
from pathlib import Path

#Installed Dependency Imports
# None

#Teatool Studio Imports
from tts_data_utils.multimission.eha import EhaContainer
from tts_data_utils.multimission.alarms import AlarmRecordContainer
from tts_utilities.logger import create_logger

#This Library Imports
from tts_dante.core.derive import Deriver, deriver_method

logger = create_logger(f'dante.eha')

class AlarmRecordDeriver(Deriver):
    NAME = 'alarm_records'


    @deriver_method(['eha'])
    def consolidated_alarm_records(self, chanvals, time_type='scet'):
        return chanvals.unique_alarms()