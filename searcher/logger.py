import datetime
from estimator.utils import write_as_file, get_SMART_logo


class Logger:
    """
    Simple logger class to output run information
    """
    def __init__(self):
        self.lines = [get_SMART_logo()]

    def add_line(self, line_string):
        """
        Adds a line to the Logger object. The logger will record the time which the statement is added
        :param line_string: String content of the line
        :return: None
        """
        now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        # print(f"{now}: {line_string}")
        self.lines.append(f"{now}: {line_string}")

    def write_out(self, file_path):
        """
        Writes the lines in the logger out onto a logging file
        :param file_path: Path of the output file (.txt)
        :return: None. Will output a .txt file.
        """
        out_string = "\n".join(self.lines)
        write_as_file(out_string, file_path)
