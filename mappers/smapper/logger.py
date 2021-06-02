import datetime
from estimator.utils import write_as_file, get_SMART_logo


class Logger:
    """
    Simple logger class to output information
    """
    def __init__(self):
        self.lines = [get_SMART_logo()]

    def add_line(self, line_string):
        now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        # print(f"{now}: {line_string}")
        self.lines.append(f"{now}: {line_string}")

    def write_out(self, file_path):
        out_string = "\n".join(self.lines)
        write_as_file(out_string, file_path)
