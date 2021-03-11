
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
    def accept_content(self, content):
        self.content = content


class Parser(parser.Parser):
    def __init__(self):
        tools.configure_logging()
        self.output_parsers = defaultdict(_OutputParser)

    def add_pattern(self, attribute, regex, cmd_name, type=int, flags="", required=False):
        if type == bool:
            logging.warning(
                "Casting any non-empty string to boolean will always "
                "evaluate to true. Are you sure you want to use type=bool?"
            )
        self.output_parsers[cmd_name].add_pattern(
            _Pattern(attribute, regex, required, type, flags)
        )

    def add_function(self, function, cmd_name):
        self.output_parsers[cmd_name].add_function(function)

    def parse(self, cmd_name, output):
        self.props = dict()
        
        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                output_parser.accept_content(content)

        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                self.props.update(output_parser.search_patterns())

        for name, output_parser in list(self.output_parsers.items()):
            if name == cmd_name:
                output_parser.apply_functions(self.props)

        return self.props
