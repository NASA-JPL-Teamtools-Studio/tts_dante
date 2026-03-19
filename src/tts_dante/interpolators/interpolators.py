import datetime
import pandas as pd
import numpy as np
import bisect
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Optional, Tuple
from scipy.interpolate import interp1d

# Teamtools Studio Imports
from tts_html_utils.core.compiler import HtmlCompiler
from tts_html_utils.core.components.text import H1, H2, P
from tts_html_utils.core.components.misc import HR
from tts_html_utils.core.components.plot import PlotBase
from tts_dtat import plot as dtat_plot

# --- 1. Abstract Base Classes ---

class Interpolator(ABC):
    """Strategy for calculating values between known data points."""
    
    @abstractmethod
    def interpolate(self, target_time, times, values, timeout=None):
        """
        Calculate an interpolated value for a specific target time.

        Args:
            target_time (float): The specific timestamp (seconds) to solve for.
            times (List[float]): A sorted list of all available timestamps.
            values (List[Any]): A list of values corresponding to the 'times' list.
            timeout (Optional[float]): Max allowed duration (seconds) before returning None.

        Returns:
            Any: The calculated value at target_time, or None if no valid data exists.
        """
        pass

class Trigger(ABC):
    """Strategy for determining the unified timeline."""
    
    @abstractmethod
    def generate_timeline(self, channels):
        """
        Generate the master list of timestamps for the alignment operation.

        Args:
            channels (Dict[str, List[Tuple[float, Any]]]): Mapping of channel names to data.

        Returns:
            List[float]: A sorted list of timestamps representing the alignment grid.
        """
        pass

# --- 2. Concrete Interpolators ---

class StepInterpolator(Interpolator):
    """Zero-order hold: uses the most recent value."""
    
    def interpolate(self, target_time, times, values, timeout=None):
        """
        Args:
            target_time (float): Solve time in seconds.
            times (List[float]): Known timestamps.
            values (List[Any]): Known data points.
            timeout (Optional[float]): Max lookback duration.
        """
        idx = bisect.bisect_right(times, target_time) - 1
        if idx < 0: return None
        if timeout and (target_time - times[idx] > timeout): return None
        return values[idx]

class SuperpositionInterpolator(Interpolator):
    """
    Reflects the uncertainty of 'when' a transition occurred.
    Returns BOTH states as a list during transition zones.
    """
    
    def interpolate(self, target_time, times, values, timeout=None):
        """
        Args:
            target_time (float): Solve time in seconds.
            times (List[float]): Known timestamps.
            values (List[Any]): Known data points.
            timeout (Optional[float]): Max lookback duration.
        """
        idx = bisect.bisect_right(times, target_time) - 1
        if idx < 0: return None
        
        if target_time == times[idx] or idx == len(times) - 1:
            return values[idx]
        
        current_val = values[idx]
        next_val = values[idx+1]
        
        if current_val == next_val:
            return current_val
        
        return [current_val, next_val]

class BoundedStepInterpolator(Interpolator):
    """The state is only valid for a fixed duration after a sample."""
    
    def __init__(self, validity_duration):
        """
        Args:
            validity_duration (float): Max seconds a sample remains valid.
        """
        self.validity_duration = validity_duration

    def interpolate(self, target_time, times, values, timeout=None):
        """
        Args:
            target_time (float): Solve time in seconds.
            times (List[float]): Known timestamps.
            values (List[Any]): Known data points.
            timeout (Optional[float]): Ignored in favor of validity_duration.
        """
        idx = bisect.bisect_right(times, target_time) - 1
        if idx < 0: return None
        if (target_time - times[idx] > self.validity_duration):
            return None
        return values[idx]

class LinearInterpolator(Interpolator):
    """First-order hold: connects points with straight lines."""
    
    def interpolate(self, target_time, times, values, timeout=None):
        """
        Args:
            target_time (float): Solve time in seconds.
            times (List[float]): Known timestamps.
            values (List[float]): Known numeric data.
            timeout (Optional[float]): Max distance to nearest sample.
        """
        if len(times) < 2: 
            return values[0] if (values and times[0] == target_time) else None
        idx = bisect.bisect_right(times, target_time) - 1
        if timeout and idx >= 0 and (target_time - times[idx] > timeout):
            return None
        f = interp1d(times, values, kind='linear', fill_value="extrapolate")
        return float(f(target_time))

class CubicInterpolator(Interpolator):
    """Smooth curve fitting for sampled physical data."""
    
    def interpolate(self, target_time, times, values, timeout=None):
        """
        Args:
            target_time (float): Solve time in seconds.
            times (List[float]): Known timestamps.
            values (List[float]): Known numeric data.
            timeout (Optional[float]): Max distance to nearest sample.
        """
        if len(times) < 4: 
            return LinearInterpolator().interpolate(target_time, times, values, timeout)
        idx = bisect.bisect_right(times, target_time) - 1
        if timeout and idx >= 0 and (target_time - times[idx] > timeout):
            return None
        f = interp1d(times, values, kind='cubic', fill_value="extrapolate")
        return float(f(target_time))

# --- 3. Concrete Triggers ---

class UnionTrigger(Trigger):
    """Creates a row for every unique timestamp across all channels."""
    
    def generate_timeline(self, channels):
        """
        Args:
            channels (Dict[str, List[Tuple[float, Any]]]): All channel data.
        """
        all_times = set()
        for data in channels.values():
            all_times.update([d[0] for d in data])
        return sorted(list(all_times))

class PeriodicTrigger(Trigger):
    """Creates a row at a fixed frequency."""
    
    def __init__(self, start, stop, step):
        """
        Args:
            start (float): Start time (seconds).
            stop (float): End time (seconds).
            step (float): Time increment (seconds).
        """
        self.start, self.stop, self.step = start, stop, step

    def generate_timeline(self, channels):
        """
        Args:
            channels (Dict[str, Any]): Ignored.
        """
        return np.arange(self.start, self.stop + self.step, self.step).tolist()

class DriverTrigger(Trigger):
    """Timeline is dictated strictly by one primary channel."""
    
    def __init__(self, driver_name):
        """
        Args:
            driver_name (str): Name of the driver channel.
        """
        self.driver_name = driver_name

    def generate_timeline(self, channels):
        """
        Args:
            channels (Dict[str, List[Tuple[float, Any]]]): All channel data.
        """
        return [d[0] for d in channels[self.driver_name]]

# --- 4. The Aligner ---

class TimeSeriesAligner:
    """Combines multiple channels into a single unified timeline."""
    
    def __init__(self, trigger, timeout=None):
        """
        Args:
            trigger (Trigger): Timeline strategy.
            timeout (Optional[float]): Default timeout for all channels.
        """
        self.trigger = trigger
        self.timeout = timeout
        self._channels = {} # type: Dict[str, List[Tuple[float, Any]]]
        self._interpolators = {} # type: Dict[str, Interpolator]

    def add_channel(self, name, data, interpolator):
        """
        Adds a data stream to the aligner.

        Args:
            name (str): Channel name.
            data (List[Dict[str, Any]]): Raw data points.
            interpolator (Interpolator): Interpolation strategy.
        """
        clean_data = sorted([(d['time'], d['val']) for d in data], key=lambda x: x[0])
        self._channels[name] = clean_data
        self._interpolators[name] = interpolator

    def align(self):
        """
        Returns:
            List[Dict[str, Any]]: Unified dataset.
        """
        timeline = self.trigger.generate_timeline(self._channels)
        results = []
        for t in timeline:
            row = {'time': t}
            for name, data in self._channels.items():
                times, values = zip(*data)
                val = self._interpolators[name].interpolate(t, times, values, self.timeout)
                row[name] = val
            results.append(row)
        return results

    @classmethod
    def create_periodic_aligner(cls, hz, start, stop, timeout=None):
        """
        Factory for periodic alignment. Returns 'TimeSeriesAligner'.
        """
        return cls(trigger=PeriodicTrigger(start, stop, 1.0/hz), timeout=timeout)

    @classmethod
    def create_forensic_aligner(cls, timeout=None):
        """
        Factory for union-based alignment. Returns 'TimeSeriesAligner'.
        """
        return cls(trigger=UnionTrigger(), timeout=timeout)

    def get_validation_plot_component(self, scenario_name):
        """
        This method is provided to try to take some of the mystecism out of this
        module. It's meant to plot the raw data for each point alongside the
        data that's been interpolated. That way if users are ever unsure
        if this library is doing the right thing, they can check it visually.

        This method is used to drive the demos of this module in the documentation

        Args:
            scenario_name (str): Title for the validation plot.

        Returns:
            PlotBase: Teamtools Studio plot component.
        """
        aligned_output = self.align()
        dtat_rows = []
        base_time = datetime.datetime(2024, 1, 1, 12, 0, 0)
        def to_dt(sec): return base_time + datetime.timedelta(seconds=sec)

        for name, raw_points in self._channels.items():
            for t, v in raw_points:
                dtat_rows.append({"scet": to_dt(t), "name": f"{name}_RAW", "value": v})
            
            for row in aligned_output:
                val = row.get(name)
                if val is not None:
                    if isinstance(val, list):
                        for sub_val in val:
                            dtat_rows.append({"scet": to_dt(row['time']), "name": f"{name}_ALIGNED", "value": sub_val})
                    else:
                        dtat_rows.append({"scet": to_dt(row['time']), "name": f"{name}_ALIGNED", "value": val})

        df = pd.DataFrame(dtat_rows)
        y_vars = []
        y_titles = []
        customize = {}
        colors = ['#0078AF', '#B85146', '#459D4C', '#E28E00']

        for i, name in enumerate(self._channels.keys()):
            raw_col = f"{name}_RAW"
            alg_col = f"{name}_ALIGNED"
            color = colors[i % len(colors)]
            y_vars.append([raw_col, alg_col])
            y_titles.append(name)

            customize[raw_col] = {
                "mode": "markers", "symbol": "circle-open", "size": 12, 
                "marker_line_width": 3, "color": color
            }
            
            interp_obj = self._interpolators[name]
            shape = 'hv' if isinstance(interp_obj, (StepInterpolator, BoundedStepInterpolator, SuperpositionInterpolator)) else ('spline' if isinstance(interp_obj, CubicInterpolator) else 'linear')
            
            customize[alg_col] = {
                "mode": "lines+markers" if not isinstance(interp_obj, SuperpositionInterpolator) else "markers",
                "symbol": "x-thin", "size": 10, 
                "line": {"width": 3.0, "color": color, "shape": shape}, 
                "connectgaps": False,
                "color": color
            }

        fig, _, _, _ = dtat_plot.make_stacked_graph(
            data=df, y_vars=y_vars, x_var="scet",
            figure_title=f"Validator: ",
            customize_dict=customize, y_axis_title=y_titles
        )
        return PlotBase(fig=fig, title=scenario_name)

def generate_validation_report():
    compiler = HtmlCompiler(title="Aligner Strategy Validation")
    compiler.add_body_component(H1("TimeSeries Aligner: Core Strategy Validation"))
    compiler.add_body_component(P("""
        Interpolation is a nuanced subject. There are several ways that one may
        want to interpolate, many of which we have probably not captured here.
        This module is built to be extensible if other interpolation strategies
        are desired in the future. Here we present a number of interpreters
        that are available in Dante so users can get an intuitive feeling for
        what the code they are calling is actually doing.
        """))

    compiler.add_body_component(P("""
        This document is meant to be an artifact that projects can use for validation
        of this module. It's a bit technical and can be hard to blindly trust, so we've
        made some plots using the various interpolators provided by this module. The
        unit tests for this library can be seen as the verification that we are doing
        the thing right, but this report is meant to be the validation that we are doing
        the right thing.
        """))
    compiler.add_body_component(P("""
        In all plots below we have taken a set of "original" data points and interpolated
        them in various ways. The "original" points are expressed as circles and the 
        interpolated points as Xs. The lines in each trace go through the Xs (or both)
        in cases where the two are aligned. Explanations of each interpolator type
        are below in the discussion of each plot.
        """))
    compiler.add_body_component(H2("Interpolators vs Triggers"))
    compiler.add_body_component(P("""
        Interpolating a point is only half the battle. Once you know where in time a point
        lies along with the points areound it you can determin its value in a number of ways:
        take the latest value as of that time, the nearest value knowing omnisciently what it
        will be, or something like a weighted average of the values around it (e.g. linear).
        """))
    compiler.add_body_component(P("""
        But before you even get that far, you need to know what the times at which you are
        doing this interpolation. This is what we call a Trigger. We provide a number of
        triggers as well as interpolators. For this you can take a naive regular cycle (PeriodicTrigger),
        choose to take one point completely at face value while interpolating the other points
        you care about at those times (DriverTrigger), or you can take any time that any of your
        data points arrive and interpolate all of the others (UnionTrigger).
        """))

    compiler.add_body_component(H2("Timeouts"))
    compiler.add_body_component(P("""
        Finally, we need to talk about timeouts. Clearly we need to be careful about how close
        data points need to be in order to be considered valid for combination. This is configurable
        and defaults to five seconds. This keeps us from trying to combine a data point with one
        that happened hours before. This is particularly important when there are data gaps, which
        is common on space missions.
        """))


    compiler.add_body_component(HR())

    # Raw sample data sets
    data_step = [{'time': 1.5, 'val': 0}, {'time': 4.5, 'val': 1}, {'time': 8.5, 'val': 0}]
    superposition_data_step = [
        {'time': 1.5, 'val': 'ENUM_A'}, 
        {'time': 2.5, 'val': 'ENUM_A'},
        {'time': 4.5, 'val': 'ENUM_B'}, 
        {'time': 6.5, 'val': 'ENUM_B'}, 
        {'time': 8.5, 'val': 'ENUM_A'},
        ]
    data_linear = [{'time': 0, 'val': 10}, {'time': 5, 'val': 25}, {'time': 10, 'val': 22}]
    data_cubic = [{'time': 0, 'val': 5}, {'time': 2, 'val': 15}, {'time': 4, 'val': 10}, 
                  {'time': 7, 'val': 30}, {'time': 9, 'val': 20}, {'time': 10, 'val': 25}]
    sparse_data = [{'time': 1.0, 'val': 10}, {'time': 9.0, 'val': 50}]
    signal_loss_data = [{'time': 1.0, 'val': 5}, {'time': 2.0, 'val': 10}, {'time': 7.0, 'val': 40}, {'time': 8.0, 'val': 45}]
    
    # 1. Periodic Resampling Demo
    compiler.add_body_component(H2("1. Periodic 1Hz Resampling: Step Interpolation and Linear Interpolation"))
    compiler.add_body_component(P("""
        The first example here potentially a naive one, but if nothing else, it
        is useful for getting the would-be validator up to speed on looking at these
        plots. In this example, we simply put a 1Hz clock on and record the latest
        avaiable value at each tick. The Valve channel is discrete, so it has been set
        to be interpolated with a StepInterpolator. The Temp data is continuous, so
        it is linearly interpolated between points.
        """))

    a1 = TimeSeriesAligner.create_periodic_aligner(hz=1, start=0, stop=10)
    a1.add_channel("Valve", data_step, StepInterpolator())
    a1.add_channel("Temp", data_linear, LinearInterpolator())
    compiler.add_body_component(a1.get_validation_plot_component("Mixed Periodic"))
    compiler.add_body_component(HR())

    # 5. Sparse Data Stress Test
    compiler.add_body_component(H2("2. High-Frequency Resampling (10Hz): Linear and Step Interpolation"))
    compiler.add_body_component(P("""
        A very similar example to the above, but instead with 10Hz refresh rate
        """))
    a5 = TimeSeriesAligner.create_periodic_aligner(hz=10, start=0, stop=10)
    a5.add_channel("Sparse_Linear", sparse_data, LinearInterpolator())
    a5.add_channel("Sparse_Step", sparse_data, StepInterpolator())
    compiler.add_body_component(a5.get_validation_plot_component("10Hz High-Res Stress Test"))
    compiler.add_body_component(HR())



    # 2. Forensic Union Demo
    compiler.add_body_component(H2("3. Union Trigger: Step Interpolation and Cubic Interpolation"))
    compiler.add_body_component(P("""
        In this example, the trigger is a UnionTrigger. This means taht any time the raw data for 
        Primary or Secondary has a data point, we will take that point and interpolate the other.
        """))
    compiler.add_body_component(P("""
        Once again for the blue plot, we have chosen to use a StepInterpolator as above. But this
        time we have chosen a CubicInterpolator for the red plot. This makes the interploation
        somewhat more organic. We have also chose to use the spline feature in Dtat/Plotly for
        smoother plotting.
        """))
    a2 = TimeSeriesAligner.create_forensic_aligner()
    a2.add_channel("Primary", data_step, StepInterpolator())
    a2.add_channel("Secondary", data_cubic, CubicInterpolator())
    compiler.add_body_component(a2.get_validation_plot_component("Forensic Union"))

    # 3. Driver Trigger Demo
    compiler.add_body_component(HR())
    compiler.add_body_component(H2("4. Driver Trigger (Primary-Driven Timeline): Step and Linear Interpolation"))
    compiler.add_body_component(P("""
        In this example we use the Driver Trigger with the Leader_Channel as the trigger channel.
        This means that any time Leader_Channel updates, Follower_Channel will be interpolated.
        If more channels were in this same interpolation, they would also be interpolated whenever
        Leader_Channel updates.
        """))
    a3 = TimeSeriesAligner(trigger=DriverTrigger(driver_name="Leader_Channel"))
    a3.add_channel("Leader_Channel", data_step, StepInterpolator())
    a3.add_channel("Follower_Channel", data_linear, LinearInterpolator())
    compiler.add_body_component(a3.get_validation_plot_component("Driver Strategy"))

    # 4. Signal Loss / Timeout Validation
    compiler.add_body_component(H2("5. Signal Loss Handling (2.0s Timeout): Linear Interpolation"))
    compiler.add_body_component(P("""
        This example shows the timeout feature. Notice the gap around 12:00:04. No data is
        interpolated here because there is no recent enough data to do so.
        """))
    compiler.add_body_component(P(
        "Between t=2 and t=7, there is a 5-second gap in data. With a 2.0s timeout, "
        "the aligner produces None, causing a break in the aligned markers."
    ))
    a4 = TimeSeriesAligner.create_periodic_aligner(hz=2, start=0, stop=10, timeout=2.0)
    a4.add_channel("Telemetry_Link", signal_loss_data, LinearInterpolator())
    compiler.add_body_component(a4.get_validation_plot_component("Timeout / Signal Gap Test"))
    compiler.add_body_component(HR())

    # 6. Kitchen Sink Forensic Audit
    compiler.add_body_component(H2("6. The Kitchen Sink: Union trigger with various interpolations"))
    compiler.add_body_component(P("""
        This example shows that more than one channel can be included in an interpolation. Here
        all three are in a Union together, meaning that any time any of the channels updates, the others
        are interpolated.
        """))
    a6 = TimeSeriesAligner.create_forensic_aligner()
    data_motion = [{'time': t, 'val': np.sin(t)} for t in [0, 2, 4, 7, 9, 10]]
    a6.add_channel("Motion_Cubic", data_motion, CubicInterpolator())
    data_switch = [{'time': 1.5, 'val': 0}, {'time': 5.5, 'val': 1}]
    a6.add_channel("Discrete_Logic", data_switch, StepInterpolator())
    data_thermal = [{'time': 0, 'val': 100}, {'time': 10, 'val': 80}]
    a6.add_channel("Thermal_Linear", data_thermal, LinearInterpolator())
    compiler.add_body_component(a6.get_validation_plot_component("Multi-Channel Forensic Audit"))
    compiler.add_body_component(HR())

    # 7. Transition Superposition Demo
    compiler.add_body_component(H2("7. Transition Superposition"))
    compiler.add_body_component(P(
        "When a transition occurs between two reports (e.g. t=1.5 to t=4.5), we don't know "
        "exactly when the state changed. The SuperpositionInterpolator plots BOTH possible "
        "states during the interval to reflect this uncertainty."
    ))
    a7 = TimeSeriesAligner.create_periodic_aligner(hz=2, start=0, stop=10)
    a7.add_channel("State_Superposition", superposition_data_step, SuperpositionInterpolator())
    compiler.add_body_component(a7.get_validation_plot_component("State Transition Superposition"))

    return compiler

if __name__ == '__main__':
    compiler = generate_validation_report()
    compiler.render_to_file("validated_report.html")
    print("Beautified validation report generated: validated_report.html")