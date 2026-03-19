import pytest
import numpy as np
from tts_dante.interpolators.interpolators import (
    StepInterpolator, LinearInterpolator, SuperpositionInterpolator, 
    BoundedStepInterpolator, CubicInterpolator, UnionTrigger, 
    PeriodicTrigger, DriverTrigger, TimeSeriesAligner
)

# --- 1. Interpolator Fixtures & Tests ---

@pytest.fixture
def basic_series():
    """Standard setup: 3 points at t=10, 20, 30 with values 100, 200, 100"""
    return [10.0, 20.0, 30.0], [100, 200, 100]

@pytest.mark.parametrize("target, expected", [
    (10.0, 100),   # Exact match
    (15.0, 100),   # Step hold
    (29.9, 200),   # Just before next point
    (5.0, None),   # Before data starts
])
def test_step_interpolator(basic_series, target, expected):
    times, values = basic_series
    assert StepInterpolator().interpolate(target, times, values) == expected

def test_step_timeout(basic_series):
    times, values = basic_series
    # t=25 is 5 seconds after t=20. Timeout=2 should return None.
    assert StepInterpolator().interpolate(25.0, times, values, timeout=2.0) is None

def test_linear_interpolator(basic_series):
    times, values = basic_series
    # Halfway between 100 and 200
    assert LinearInterpolator().interpolate(15.0, times, values) == 150.0

def test_superposition_interpolator(basic_series):
    times, values = basic_series
    interp = SuperpositionInterpolator()
    # At exact point: no uncertainty
    assert interp.interpolate(20.0, times, values) == 200
    # Between points with different values: returns both
    assert interp.interpolate(15.0, times, values) == [100, 200]
    # Between points with same value: returns single value (if values were 100, 100)
    assert interp.interpolate(25.0, [20, 30], [100, 100]) == 100

def test_bounded_step_interpolator():
    times, values = [10.0], [100]
    interp = BoundedStepInterpolator(validity_duration=5.0)
    assert interp.interpolate(12.0, times, values) == 100
    assert interp.interpolate(16.0, times, values) is None

# --- 2. Trigger Tests ---

def test_union_trigger():
    channels = {
        "C1": [(1.0, 'a'), (3.0, 'b')],
        "C2": [(2.0, 'x'), (3.0, 'y')]
    }
    assert UnionTrigger().generate_timeline(channels) == [1.0, 2.0, 3.0]

def test_periodic_trigger():
    # Start 0, Stop 2, Step 1 -> [0.0, 1.0, 2.0]
    trigger = PeriodicTrigger(0, 2, 1)
    assert trigger.generate_timeline({}) == [0.0, 1.0, 2.0]

def test_driver_trigger():
    channels = {
        "Master": [(10.0, 1), (20.0, 2)],
        "Slave": [(15.0, 9)]
    }
    assert DriverTrigger("Master").generate_timeline(channels) == [10.0, 20.0]

# --- 3. Aligner Integration Tests ---

def test_aligner_integration():
    """Tests multiple channels with different strategies aligned together."""
    aligner = TimeSeriesAligner.create_periodic_aligner(hz=1, start=0, stop=2)
    
    # Data at t=0.5
    aligner.add_channel("StepCh", [{'time': 0.5, 'val': 10}], StepInterpolator())
    # Data from t=0 to t=2
    aligner.add_channel("LinCh", [{'time': 0, 'val': 0}, {'time': 2, 'val': 20}], LinearInterpolator())
    
    results = aligner.align()
    
    # t=0.0 -> StepCh=None, LinCh=0
    assert results[0]['time'] == 0.0
    assert results[0]['StepCh'] is None
    assert results[0]['LinCh'] == 0.0

    # t=1.0 -> StepCh=10 (held from 0.5), LinCh=10 (linear)
    assert results[1]['time'] == 1.0
    assert results[1]['StepCh'] == 10
    assert results[1]['LinCh'] == 10.0

def test_aligner_sorting():
    """Ensure add_channel handles out-of-order input data."""
    aligner = TimeSeriesAligner(UnionTrigger())
    unsorted_data = [{'time': 30, 'val': 3}, {'time': 10, 'val': 1}]
    aligner.add_channel("Ch", unsorted_data, StepInterpolator())
    
    # The internal storage should be sorted
    times = [d[0] for d in aligner._channels["Ch"]]
    assert times == [10, 30]

def test_cubic_fallback():
    """Cubic should fallback to Linear if < 4 points."""
    times, values = [0, 10], [0, 100]
    interp = CubicInterpolator()
    # Should perform linear interpolation (5.0) instead of crashing
    assert interp.interpolate(5.0, times, values) == 50.0