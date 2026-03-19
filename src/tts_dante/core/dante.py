#Standard Library Imports
import pdb

#Installed Dependency Imports
# None

#Teatool Studio Imports
from tts_utilities.logger import create_logger


#This Library Imports
from tts_data_utils.invulnerable_data_manager.invulnerable_data_manager import InvulnerableDataManager
from tts_data_utils.invulnerable_data_manager.utilities import invulnerable, exec_invulnerable
from tts_data_utils.invulnerable_data_manager.batch import AllDataBatch, UntaggedBatch

logger = create_logger(__name__)

class Dante(InvulnerableDataManager):
    """
    The central management class for the Dante data derivation framework.

    Inherits from InvulnerableDataManager to provide robust data loading and management.
    Unlike Dexter, which focuses on dispositioning existing data, Dante is designed
    to orchestrate the derivation of new data products via a series of registered
    'Derivers'.

    Attributes:
        _derivers (list): A list of initialized deriver instances managed by this class.
    """
    def __init__(self):
        super().__init__()
        self._derivers = []

    # :: Deriving
    def init_deriver(self, deriver_cls):
        """
        Instantiates and registers a new deriver.

        This method safely attempts to create an instance of the provided
        deriver class using `exec_invulnerable`. If successful, the
        instance is added to the internal list of active derivers.

        Args:
            deriver_cls (class): The class of the deriver to initialize.
                                 Must accept the Dante instance as an argument.
        """
        # TO DO: check for already initialized derivers
        # this code came from Dexter ans is wrong for this
        # context
        #
        # if self.all_output_data.has_data(deriver_cls.OUTPUT_NAME):
        #     raise ValueError(f'Output Data Container "{name}" initialized twice')

        new_deriver = exec_invulnerable(deriver_cls, self)

        if new_deriver is not None:
            self._derivers.append(new_deriver)
            
    def derive_all(self):
        """
        Executes the derivation logic for all registered derivers.

        Iterates through the list of initialized derivers and calls their
        `derive` method to generate new data products.
        """
        for deriver in self._derivers:
            new_data = deriver.derive()
            
    def _impl_init_data(self, *args, **kwargs):
        """
        Implementation hook for initializing data containers.

        Currently a placeholder override for the parent class's hook.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        return