import sqlite3, yaml, yamlordereddictloader
from collections import OrderedDict
from data_structures.feature_script import FeatureScript
from utils import *

DEFAULT_DB_PATH = "data/intelligent_primitive_component_library.db"


class DatabaseHandler:
    """
    Communicates with SQLite3 package to extract information using SQL
    Singleton defined at the end of file
    """

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        self.table = "PrimitiveComponents"

    def set_ipcl_table(self, table_name: str):
        """
        Set the table to read IPCL data from. This allows the user to have multiple configurations
        :param table_name: table to be set to
        :return: None
        """
        self.table = table_name

    def get_component_feature(self, component_name, feature):
        """
        Executes SQL to get and parse parameters for the energy function
        :return: Dict of {action : FeatureScript}
        """
        features = {"energy": "EnergyFunction", "area": "AreaFunction", "cycle": "CycleFunction"}
        sql_results = self.cursor.execute("SELECT ComponentName, Action, Arguments, DefaultValues, %s "
                                          % features[feature] +
                                          "FROM \"%s\" WHERE ComponentName = \"%s\""
                                          % (self.table, component_name))
        results_array = sql_results.fetchall()
        action_dict = OrderedDict()
        for (name, action, arguments, default_values, function) in results_array:
            args = parse_as_list(arguments)
            vals = parse_as_list(default_values)
            action_dict[action] = FeatureScript(function, args, vals)
        return action_dict

    def is_primitive_component(self, component_name: str):
        """
        Checks if component_name is a primitive component as defined in DB
        :param component_name: component to be checked
        :return: Boolean whether in IPCL
        """
        sql_results = self.cursor.execute("SELECT ComponentName FROM %s " % self.table +
                                          "WHERE ComponentName = \"%s\"" % component_name)
        return len(sql_results.fetchall()) != 0


class YAMLHandler:
    """
    Uses PyYAML and Yaml Ordered Dict Loader to read YAML inputs
    """
    yaml_path = str()
    dict_repr = OrderedDict()  # Representation of YAML as an ordered Dict()

    def __init__(self, yaml_path):
        with open(yaml_path) as f:
            yaml_data = yaml.load(f, Loader=yamlordereddictloader.Loader)
        self.yaml_path = yaml_path
        self.dict_repr = yaml_data

    def get_as_dict(self):
        return self.dict_repr


database_handler = DatabaseHandler()
