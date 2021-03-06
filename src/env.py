"""
This file provides easy access to run mode settings of the Green Paths route planner app. 

The default values can be overridden as necessary, e.g. set research_mode to True if additional
path properties (such as list of edge IDs) are needed. It is recommended to disable unused
features (walking_enabled, quiet_paths_enabled etc.) to allow smaller memory usage and faster routing. 

"""

import os
from typing import List

graph_subset: bool = os.getenv('GRAPH_SUBSET', 'False') == 'True'
graph_file: str = r'graphs/kumpula.graphml' if graph_subset else r'graphs/hma.graphml'

test_mode: bool = False             # only used by pytest

research_mode: bool = False         # set to True for additional path properties
walking_enabled: bool = True        # enables/disables walk cost calculation
cycling_enabled: bool = True        # enables/disables bike cost calculation
quiet_paths_enabled: bool = True    # enables/disables noise cost calculation
clean_paths_enabled: bool = True    # enables/disables air quality cost calculation
gvi_paths_enabled: bool = True      # enables/disables green view cost calculation

# the default sensitivities for exposure optimized routing can be overridden with these:
noise_sensitivities: List[float] = []
aq_sensitivities: List[float] = []
gvi_sensitivities: List[float] = []
