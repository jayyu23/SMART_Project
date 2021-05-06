from collections import OrderedDict
from typing import final

"""
Provides a sandbox environment in order to run the exec() script on values in the database
Allows the methods in math
Disallows the keywords identified in illegal
"""

ILLEGAL = ["open", "import", "exec", "eval", "compile", "__", "exit", "locals", "global", "quit", "zip", "def",
           "class ", "super", "object", "del ", "del\\", "delattr", "input", "dir", "self", "assert"]


class FeatureScript:
    """
    FeatureScript is a wrapper around a Python script as read in from the database. It cleans the script before
    performing the exec() function
    """
    default_values = OrderedDict()  # String -> string dict, arguments to default_values
    script = str()  # Script contained

    @staticmethod
    def check_is_clean(code_string: str) -> bool:
        """
        Checks if the code string extracted from IPCL contains any illegal keyword, prepare for exec()
        :param code_string: string representation of the Python code
        :return: if code can be exec() safely, no illegal keywords
        """
        for keyword in ILLEGAL:
            if keyword in str(code_string):
                print("Illegal keyword found: %s" % keyword)
                return False
        return True

    def __init__(self, script, arg_array, default_values_array):
        """
        Creates a sandbox environment where script can be executed safely
        :param script: code-string to be executed
        :param arg_array : array of arguments for the execution
        :param default_values_array : array of instantiated values defined in args
        """
        # Check the arg_array and value_array
        # Perform type checks on arg_array and defaults array and range check to ensure defaults are there
        assert (isinstance(arg_array, list) and isinstance(default_values_array, list))
        assert (len(arg_array) == len(default_values_array))
        self.repeat = 1
        for i in range(len(arg_array)):
            assert (self.check_is_clean(arg_array[i]) and self.check_is_clean(default_values_array[i]))
            self.default_values[arg_array[i]] = default_values_array[i]

        # Check and format the script
        assert (self.check_is_clean(script))
        self.script = "def script({0}):\n\t{1}".format(",".join(arg_array), "\n\t".join(
            script.replace("\r", "").split("\n")) + "\nout_var = script(" + ",".join(arg_array) + ")")

    def __repr__(self):
        return "Script with default args: " + str(self.default_values)

    def execute(self, runtime_args: OrderedDict = None):
        """
        Executes the script once. Because script exec() happens in an object method, all local variables
        created here are destroyed at the end of the method
        :return: out_var as defined in the script. See Constructor above
        """
        # print("Runtime args:", runtime_args)
        # Parse in runtime arguments and create local variables
        for arg in self.default_values:
            value = runtime_args[arg] if (runtime_args and arg in runtime_args) else self.default_values[arg]
            # Check cleanliness again
            assert (self.check_is_clean(arg) and self.check_is_clean(value))
            if str(arg).strip() and str(value).strip():
                exec(str(arg) + " = " + str(value))
        exec(self.script)
        return locals()['out_var']