import datetime
from estimator.utils import write_as_file


class Logger:
    """
    Simple logger class to output information
    """
    def __init__(self):
        self.lines = []

    def add_line(self, line_string):
        now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        self.lines.append(f"{now}: {line_string}")

    def write_out(self, file_path):
        out_string = "\n".join(self.lines)
        write_as_file(out_string, file_path)
