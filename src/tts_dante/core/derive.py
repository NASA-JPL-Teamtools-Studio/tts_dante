#Standard Library Imports
import re
import traceback
from enum import Enum, auto
from inspect import ismethod
from functools import wraps

#Installed Dependency Imports
# None

#Teatool Studio Imports
from tts_data_utils.invulnerable_data_manager.utilities import invulnerable
from tts_papertrail.base import RichText
from tts_utilities.logger import create_logger

#This Library Imports
# None

log = create_logger(__name__)

RE_HEXCOLOR = re.compile(r'^#?([0-9a-fA-F]{6})$')

def invulnerable_method(required, optional=None, batch=None, approved=True, method_name='invulnerable method'):
    """
    Decorator factory to create a robust data processing method wrapper.

    Ensures that required data is available before executing the decorated function
    and wraps execution in an `invulnerable` block to prevent crashes from exceptions.

    Args:
        required (list[str]): Names of data items required for the method.
        optional (list[str], optional): Names of optional data items.
        batch (str, optional): Name of a specific data batch to use.
        approved (bool, optional): Whether the method is approved for execution. Defaults to True.
        method_name (str, optional): A descriptive name for logging purposes.

    Returns:
        function: The decorated function wrapper.
    """
    def wrapper_outer(func):
        @invulnerable
        @wraps(func)
        def wrapper_inner(self):
            func_fullname = "{}.{}".format(self.__class__.__name__, func.__name__)
            
            if batch is None:
                batches = [self.dante.all_input_data]
            else:
                batcher = self.dante.get_batcher(batch)
                if batcher is None:
                    log.critical(f'Missing batch type {batch} for {method_name} {func_fullname}')
                    return
                batches = batcher.batches
                
            for data_batch in batches:
                data = []
                for name in required:
                    data.append(data_batch.get_data(name))
                missing_names = [_[0] for _ in zip(required, data) if _[1] is None]
                if len(missing_names) > 0:
                    missing_names_str = ' '.join([f'"{_}"' for _ in missing_names])
                    log.critical(f'Missing data {missing_names_str} in {method_name} for {self.NAME} {func_fullname}')
                    return
                if optional:
                    for name in optional:
                        data.append(self.dante.get_data(name))

                result_data = func(self, *data)

                return result_data

        wrapper_inner._is_approved_disposition = approved
        return wrapper_inner
    return wrapper_outer

#is this really a value add here?
def deriver_method(required, optional=None, batch=None, approved=True):
    """
    Decorator for defining a data derivation method.

    This is a specialized version of `invulnerable_method` specifically for
    deriver functions.

    Args:
        required (list[str]): Names of required data items.
        optional (list[str], optional): Names of optional data items.
        batch (str, optional): Name of a specific data batch to use.
        approved (bool, optional): Whether the derivation is approved. Defaults to True.

    Returns:
        function: The decorated derivation method.
    """
    return invulnerable_method(required, optional=None, batch=None, approved=True, method_name='deriver method')

class Deriver:
    """
    Base class for implementing data derivation logic.

    Subclasses must define a `NAME` attribute and implement derivation methods
    decorated with `@deriver_method`. The `derive` method automatically discovers
    and executes these methods to produce new data products.

    Attributes:
        DERIVER_NAME (str or None): Placeholder for the specific deriver's name.
                                    Subclasses should override `NAME` instead.
    """
    DERIVER_NAME = None

    def __init__(self, dante):
        """
        Initializes the Deriver instance.

        Args:
            dante (Dante): The parent Dante manager instance.

        Raises:
            Exception: If the subclass does not define a `NAME` attribute.
        """

        if self.NAME is None:
            raise Exception('All derivers must have NAME defined.')

        self.dante = dante
        self.__post_init__()
        
    def __post_init__(self):
        """Hook for post-initialization logic in subclasses."""
        return

    def derive(self):
        """
        Executes all approved derivation methods within this class.

        Iterates over methods decorated with `@deriver_method`, executes them,
        and registers any valid resulting data products with the Dante manager.
        Also prevents duplicate execution if data for this deriver already exists.
        """
        for _name in dir(self):
            if self.dante.all_output_data.has_data(self.NAME):
                log.warning(f'Output Data Container "{self.NAME}" initialized twice')
                log.info(f'Skipping duplicate derivation {methodname}')

            _attr = getattr(self, _name)
            if ismethod(_attr) and hasattr(_attr, '_is_approved_disposition'):
                methodname = f'{self.__class__.__name__}.{_name}'
                if _attr._is_approved_disposition:
                    log.info(f'Running derivation {methodname}')
                    new_data = _attr()
                    if (new_data is not None) and (new_data.valid):
                        self.dante.all_output_data.set_data_one(f'{self.NAME}.{_name}', new_data)
                    else:
                        log.warning(f'Failed to initialize "{self.NAME}" output data container')
                else:
                    log.info(f'Skipping unapproved derivation {methodname}')