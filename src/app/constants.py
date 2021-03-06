from enum import Enum
from typing import Dict


class TravelMode(Enum):
    WALK = 'walk'
    BIKE = 'bike'

class RoutingMode(Enum):
    CLEAN = 'clean' # i.e. "fresh air"
    QUIET = 'quiet'
    GREEN = 'green'

class PathType(Enum):
    SHORT = 'short'
    CLEAN = RoutingMode.CLEAN.value
    QUIET = RoutingMode.QUIET.value
    GREEN = RoutingMode.GREEN.value


cost_prefix_dict: Dict[TravelMode, Dict[RoutingMode, str]] = {
    TravelMode.WALK: {
        RoutingMode.CLEAN: 'c_aq_',
        RoutingMode.QUIET: 'c_n_',
        RoutingMode.GREEN: 'c_g_'
    },
    TravelMode.BIKE: {
        RoutingMode.CLEAN: 'c_aq_b_',
        RoutingMode.QUIET: 'c_n_b_',
        RoutingMode.GREEN: 'c_g_b_'
    }
}

class RoutingException(Exception):
    pass

class ErrorKeys(Enum):
    DESTINATION_NOT_FOUND = 'destination_not_found'
    ORIGIN_NOT_FOUND = 'origin_not_found'
    ORIGIN_OR_DEST_NOT_FOUND = 'origin_or_destination_not_found'
    PATHFINDING_ERROR = 'error_in_path_finding'
    PATH_PROCESSING_ERROR = 'error_in_path_processing'
    OD_SAME_LOCATION = 'od_are_same_location'
    NO_REAL_TIME_AQI_AVAILABLE = 'no_real_time_aqi_available'
    INVALID_TRAVEL_MODE_PARAM = 'invalid_travel_mode_in_request_params'
    INVALID_EXPOSURE_MODE_PARAM = 'invalid_exposure_mode_in_request_params'
    AQI_ROUTING_NOT_AVAILABLE = 'air_quality_routing_not_available'
    UNKNOWN_ERROR = 'unknown_error'