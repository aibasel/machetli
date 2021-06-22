from collections import defaultdict
import logging

from lab import parser
from lab import tools


class _Pattern(parser._Pattern):
    def search(self, content, cmd_name):
        found_props = {}
        match = self.regex.search(content)
        if match:
            try:
                value = match.group(self.group)
            except IndexError:
                logging.error(
                    f"Attribute {self.attribute} not found for pattern {self} in "
                    f"output of command {cmd_name}."
                )
            else:
                value = self.type_(value)
                found_props[self.attribute] = value
        elif self.required:
            logging.error(
                f'Pattern "{self}" not found in output of command {cmd_name}')
        return found_props


class _OutputParser(parser._FileParser):
    def accept_data(self, cmd_name, content):
        # Only calling this member "filename" so inherited function 
        # search_patterns does not need to be changed
        self.filename = cmd_name
        self.content = content


class Parser(parser.Parser):
    def __init__(self):
        tools.configure_logging()
        self.output_parsers = defaultdict(_OutputParser)

    def add_pattern(self, attribute, regex, cmd_names, type=int, flags="", required=False):
        if type == bool:
            logging.warning(
                "Casting any non-empty string to boolean will always "
                "evaluate to true. Are you sure you want to use type=bool?"
            )
        for name in tools.make_list(cmd_names):
            self.output_parsers[name].add_pattern(
                _Pattern(attribute, regex, required, type, flags)
            )

    def add_function(self, functions, cmd_names):
        for name in tools.make_list(cmd_names):
            for function in tools.make_list(functions):
                self.output_parsers[name].add_function(function)

    def parse(self, cmd_name, output):
        self.props = dict()

        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                output_parser.accept_data(name, output)

        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                self.props.update(output_parser.search_patterns())

        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                output_parser.apply_functions(self.props)

        return self.props


if __name__ == "__main__":
    import pprint
    parser = Parser()
    parser.add_pattern(attribute="attr", regex=r"(world)", cmd_names="test", type=bool)
    result = parser.parse(cmd_name="test", output="Hello world!")
    pprint.pprint(result)
