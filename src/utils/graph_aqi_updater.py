import time
import ast
import random
import traceback
import pandas as pd
from os import listdir
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from utils.graph_handler import GraphHandler
import utils.aq_exposures as aq_exps
from utils.logger import Logger
from typing import List, Set, Dict, Tuple, Optional

class GraphAqiUpdater:
    """GraphAqiUpdater triggers an AQI to graph update if new AQI data is available in /aqi_cache.

    Attributes:
        graph_handler: A GraphHandler object that can update aqi values to a graph.
        aqi_dir (str): A path to an aqi_cache -directory (e.g. 'aqi_cache/').
        aqi_data_wip: The name of an aqi data csv file that is currently being updated to a graph.
        aqi_data_latest: The name of the aqi data csv file that was last updated to a graph.
        aqi_data_updatetime: datetime.utcnow() of the latest aqi update.
        scheduler: A BackgroundScheduler object that will periodically check for new aqi data and
            update it to a graph if available.
    """

    def __init__(self, logger: Logger, G: GraphHandler, aqi_dir: str = 'aqi_cache/', start: bool = False):
        self.log = logger
        self.G = G
        self.sens = aq_exps.get_aq_sensitivities()
        self.aqi_update_status = ''
        self.aqi_dir = aqi_dir
        self.aqi_data_wip = ''
        self.aqi_data_latest = ''
        self.aqi_data_updatetime = None
        self.scheduler = BackgroundScheduler()
        self.check_interval = 5 + random.randint(1, 10)
        self.scheduler.add_job(self.maybe_read_update_aqi_to_graph, 'interval', seconds=self.check_interval, max_instances=2)
        if (start == True): self.start()

    def start(self):
        self.log.info('starting graph aqi updater with check interval (s): '+ str(self.check_interval))
        self.scheduler.start()

    def get_aqi_update_status_response(self):
        return { 
            'b_updated': self.bool_graph_aqi_is_up_to_date(), 
            'latest_data': self.aqi_data_latest, 
            'update_time_utc': self.get_aqi_update_time_str(), 
            'updated_since_secs': self.get_aqi_updated_since_secs()
            }

    def maybe_read_update_aqi_to_graph(self):
        """Triggers an AQI to graph update if new AQI data is available and not yet updated or being updated.
        """
        new_aqi_data_csv = self.new_aqi_data_available()
        if (new_aqi_data_csv is not None):
            try:
                self.read_update_aqi_to_graph(new_aqi_data_csv)
            except Exception:
                self.aqi_update_status = 'could not complete AQI update from: '+ new_aqi_data_csv
                self.log.error(self.aqi_update_status)
                traceback.print_exc()
                time.sleep(60)

    def get_expected_aqi_data_name(self) -> str:
        """Returns the name of the expected latest aqi data csv file based on the current time, e.g. aqi_2019-11-11T17.csv.
        """
        curdt = datetime.utcnow().strftime('%Y-%m-%dT%H')
        return 'aqi_'+ curdt +'.csv'

    def get_aqi_update_time_str(self) -> str:
        return self.aqi_data_updatetime.strftime('%y/%m/%d %H:%M:%S') if self.aqi_data_updatetime is not None else None

    def get_aqi_updated_since_secs(self) -> int:
        if (self.aqi_data_updatetime is not None):
            updated_since_secs = (datetime.utcnow() - self.aqi_data_updatetime).total_seconds()
            return int(round(updated_since_secs))
        else:
            return None

    def bool_graph_aqi_is_up_to_date(self) -> bool:
        """Returns True if the latest AQI is updated to graph, else returns False. This can be attached to an API endpoint
        from which clients can ask whether the green path service supports real-time AQ routing at the moment.
        """
        if (self.aqi_data_updatetime is None):
            return False
        elif (self.get_aqi_updated_since_secs() < 60 * 70):
            return True
        else:
            return False

    def new_aqi_data_available(self) -> str:
        """Returns the name of a new AQI csv file if it's not yet updated or being updated to a graph and it exists in aqi_dir.
        Else returns None.
        """
        new_aqi_available = None
        aqi_update_status = ''

        aqi_data_expected = self.get_expected_aqi_data_name()
        if (aqi_data_expected == self.aqi_data_latest):
            aqi_update_status = 'latest AQI was updated to graph'
        elif (aqi_data_expected == self.aqi_data_wip):
            aqi_update_status = 'AQI update already in progress'
        elif (aqi_data_expected in listdir(self.aqi_dir)):
            aqi_update_status = 'AQI update will be done from: '+ aqi_data_expected
            new_aqi_available = aqi_data_expected
        else:
            aqi_update_status = 'expected AQI data is not available ('+ aqi_data_expected +')'
        
        if (aqi_update_status != self.aqi_update_status):
            if ('not available' in aqi_update_status):
                self.log.warning(aqi_update_status)
            else:
                self.log.info(aqi_update_status)
            self.aqi_update_status = aqi_update_status
        return new_aqi_available

    def get_aq_update_attrs(self, aqi_exp: Tuple[float, float]):
        aq_costs = aq_exps.get_aqi_costs(aqi_exp, self.sens, length=aqi_exp[1])
        return { 'aqi': aqi_exp[0], **aq_costs }
    
    def read_update_aqi_to_graph(self, aqi_updates_csv: str):
        self.aqi_data_wip = aqi_updates_csv
        # read aqi update csv
        field_type_converters = { 'uvkey': ast.literal_eval, 'aqi_exp': ast.literal_eval }
        edge_aqi_updates = pd.read_csv(self.aqi_dir + aqi_updates_csv, converters=field_type_converters)

        # ensure that all edges will get aqi value
        edge_key_count = self.G.edge_gdf['uvkey'].nunique()
        update_key_count = edge_aqi_updates['uvkey'].nunique()
        if (edge_key_count != update_key_count):
            self.log.warning('Non matching edge key vs update key counts: '+ str(edge_key_count) +' '+ str(update_key_count))

        # validate aqi_exps to update
        aqi_data_ok = self.validate_aqi_exps(edge_aqi_updates)
        if (aqi_data_ok == False):
            self.log.warning('Invalid aqi_exp data in aqi_updates_csv')
        
        # update aqi_exp to edge_gdf
        edge_gdf_copy = self.G.edge_gdf.copy()
        if ('aqi_exp' in edge_gdf_copy.columns): 
            edge_gdf_copy = edge_gdf_copy.drop(columns=['aqi_exp']).merge(edge_aqi_updates, on='uvkey', how='left')
        else:
            edge_gdf_copy = edge_gdf_copy.merge(edge_aqi_updates, on='uvkey', how='left')
        self.G.set_edge_gdf(edge_gdf_copy)
        self.log.debug('joined edge_gdf has columns: ' + str(self.G.edge_gdf.columns))

        # validate aqi_exp updates to edge_gdf
        aqi_edge_updates_ok = self.validate_aqi_exps(self.G.edge_gdf)
        if (aqi_edge_updates_ok == False):
            self.log.warning('Failed to update all aqi_exps to edge_gdf')

        # prepare dictionary of aqi attributes to update
        edge_aqi_updates['aq_updates'] = [self.get_aq_update_attrs(aqi_exp) for aqi_exp in edge_aqi_updates['aqi_exp']]
        self.G.update_edge_attr_to_graph(edge_gdf=edge_aqi_updates, from_dict=True, df_attr='aq_updates')
        self.log.info('AQI update succeeded')
        self.aqi_data_updatetime = datetime.utcnow()
        self.aqi_data_latest = aqi_updates_csv
        self.aqi_data_wip = ''

    def validate_aqi_exps(self, edge_gdf: pd.DataFrame) -> bool:
        def validate_aqi_exp(aqi_exp):
            if (not isinstance(aqi_exp, tuple)):
                return False
            elif (not isinstance(aqi_exp[0], float)):
                return False
            elif (not isinstance(aqi_exp[1], float)):
                return False
            else:
                return True

        edge_gdf_copy = edge_gdf.copy()
        edge_gdf_copy['exp_ok'] = [validate_aqi_exp(aqi_exp) for aqi_exp in edge_gdf_copy['aqi_exp']]

        row_count = len(edge_gdf_copy.index)
        aqi_exp_count = len(edge_gdf_copy[edge_gdf_copy['exp_ok'] == True].index)

        if (row_count == aqi_exp_count):
            return True
        else:
            self.log.warning('row count: '+ str(row_count) +' of which has valid aqi exp: '+ str(aqi_exp_count))
            return False