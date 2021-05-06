"""
Utility functions, used for tasks such as string handling
"""
from collections import OrderedDict
import yaml, yamlordereddictloader


def remove_brackets(string: str) -> str:
    """
    Removes the square brackets [] at the beginning and end of a string
    :param string: Original string
    :return: String without square brackets []
    """
    string = string.strip()
    string = string[1:] if string[0] == "[" else string
    string = string[:len(string) - 1] if string[-1] == "]" else string
    return string


def parse_as_list(string: str) -> []:
    """
    Parses a Python array stored in the .db as a STRING into a list object
    :param string:
    :return:
    """
    array_string = remove_brackets(string)
    array = array_string.split(",")
    array = [x.strip() for x in array]
    return array


def get_SMART_logo():
    """
    Prints out the SMART logo in terminal as big text
    :return: SMART logo and header
    """
    out = """
░██████╗███╗░░░███╗░█████╗░██████╗░████████╗
██╔════╝████╗░████║██╔══██╗██╔══██╗╚══██╔══╝
╚█████╗░██╔████╔██║███████║██████╔╝░░░██║░░░
░╚═══██╗██║╚██╔╝██║██╔══██║██╔══██╗░░░██║░░░
██████╔╝██║░╚═╝░██║██║░░██║██║░░██║░░░██║░░░
╚═════╝░╚═╝░░░░░╚═╝╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░\n"""
    out += "Shensilicon Microchip Architectural Reference Tool\n"
    out += ("=" * 50)
    return out


def write_as_file(text: str, out_path: str):
    """
    Outputs string into a file
    :param text: text to be output
    :param out_path: file to be written to. Must have write permission
    :return: None
    """
    file = open(out_path, mode="w", encoding="utf-8")
    file.write(text)
    file.close()


def parse_method_notation(method_string: str):
    """
    Parses in notation following Python object.method(arg1=v1, arg2=v2, arg3=v3)
    :param method_string: the object-method string notation
    :return: dict with keys 'object', 'method', 'arguments'
    """
    out_dict = OrderedDict({'object': None, 'method': None, 'arguments': OrderedDict()})
    # Parse in the object.method()
    if '.' in method_string:
        out_dict['object'], method_string = method_string.split('.', maxsplit=1)
    # Parse brackets:
    if '(' in method_string:
        out_dict['method'], method_string = method_string.split('(', maxsplit=1)
        if method_string[-1] == ')':
            method_string = method_string[:-1]  # Remove end bracket
        # Parse arguments
        for i in method_string.split(","):
            if "=" in i:
                arg, val = i.split("=", maxsplit=1)
                out_dict['arguments'][arg.strip()] = val.strip()
    else:
        out_dict['method'] = method_string
    return out_dict


def read_yaml_file(yaml_path):
    with open(yaml_path) as f:
        yaml_data = yaml.load(f, Loader=yamlordereddictloader.Loader)
    return yaml_data
