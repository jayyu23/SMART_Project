import sqlite3, yaml, yamlordereddictloader
from collections import OrderedDict
from functools import lru_cache

from estimator.data_structures.feature_script import FeatureScript
from estimator.utils import *

DEFAULT_DB_PATH = "estimator/database/intelligent_primitive_component_library.db"
DEFAULT_TABLE = "TH2Components"

class DatabaseHandler:
    """
    Communicates with SQLite3 package to extract information using SQL
    Singleton defined at the end of file
    """

    def __init__(self, db_path=DEFAULT_DB_PATH, db_table=DEFAULT_TABLE):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.table = db_table if db_table else "PrimitiveComponents"

    def set_ipcl_table(self, table_name: str):
        """
        Set the table to read IPCL database from. This allows the user to have multiple configurations
        :param table_name: table to be set to
        :return: None
        """
        self.table = table_name

    def get_component_feature(self, component_name, feature, args, vals):
        """
        Executes SQL to get and parse parameters for the energy function
        :return: Dict of {action : FeatureScript}
        """
        features = {"energy": "EnergyFunction", "area": "AreaFunction", "cycle": "CycleFunction"}
        sql_results = self.cursor.execute("SELECT ComponentName, Action, %s "
                                          % features[feature] +
                                          "FROM \"%s\" WHERE ComponentName = \"%s\""
                                          % (self.table, component_name))
        results_array = sql_results.fetchall()
        action_dict = OrderedDict()
        for (name, action, function) in results_array:
            action_dict[action] = FeatureScript(function, args, vals)
        return action_dict

    @lru_cache(None)
    def is_primitive_component(self, component_name: str):
        """
        Checks if component_name is a primitive component as defined in DB
        :param component_name: component to be checked
        :return: Boolean whether in IPCL
        """
        sql_results = self.cursor.execute("SELECT ComponentName FROM %s " % self.table +
                                          "WHERE ComponentName = \"%s\"" % component_name)
        return len(sql_results.fetchall()) != 0

    @lru_cache(None)
    def get_default_arguments(self, component_name):
        sql_results = self.cursor.execute(f"SELECT Arguments, DefaultValues FROM {self.table} "
                                          f"WHERE ComponentName = \"{component_name}\"")

        args, vals = sql_results.fetchone()
        args_list, vals_list = parse_as_list(args), parse_as_list(vals)
        return {args_list[i]: vals_list[i] for i in range(len(args_list))}


database_handler = DatabaseHandler()
