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
        return found_props


class _OutputParser(parser._FileParser):
    def accept_data(self, cmd_name, content):
        # Only calling this member "filename" so inherited function
        # search_patterns does not need to be changed
        self.filename = cmd_name
        self.content = content


class Parser(parser.Parser):
    """Parse stdout and stderr strings.

    Strongly influenced by the `parser implementation of Lab
    <https://lab.readthedocs.io/en/latest/lab.experiment.html#lab.parser.Parser>`_,
    hence the partially identical documentation.
    """
    def __init__(self):
        tools.configure_logging()
        self.output_parsers = defaultdict(_OutputParser)

    def add_pattern(self, attribute, regex, cmd_names, type=int, flags=""):
        """Look for *regex* in stdout and stderr of the executed runs with names *cmd_names*
        and cast what is found in brackets to *type*.
        
        Store the parsing result of this pattern under the name *attribute* in the
        properties dictionary returned by :meth:`parse(cmd_name, output) <minimizer.parser.Parser.parse>`.

        *flags* must be a string of Python regular expression flags (see
        https://docs.python.org/3/library/re.html). E.g., ``flags="M"``
        lets "^" and "$" match at the beginning and end of each line,
        respectively.

        Usage example:

        .. code-block:: python
        
            parser = Parser()

            parser.add_pattern("translator_facts",
                   r"Translator facts: (\d+)", "amazing_run")
        """
        if type == bool:
            logging.warning(
                "Casting any non-empty string to boolean will always "
                "evaluate to true. Are you sure you want to use type=bool?"
            )
        for name in tools.make_list(cmd_names):
            self.output_parsers[name].add_pattern(
                _Pattern(attribute, regex, required=False, type_=type, flags=flags)
            )

    def add_function(self, functions, cmd_names):
        """Add *functions* to parser which are called on the output strings
        of the executed runs *cmd_names*. *functions* and *cmd_names* can
        both be used for single arguments as well as for argument lists.

        Functions are applied **after** all patterns have been evaluated.

        The function is passed the output strings and the properties
        dictionary. It must manipulate the passed properties dictionary.
        The return value is ignored.

        Usage example:

        .. code-block:: python

            parser = Parser()

            def facts_tracker(content, props):
                props["translator_facts"] = re.findall(r"Translator facts: (\d+)", content)

            parser.add_function(facts_tracker, ["amazing_run", "superb_run"])
        """
        for name in tools.make_list(cmd_names):
            for function in tools.make_list(functions):
                self.output_parsers[name].add_function(function)

    def parse(self, cmd_name, output):
        """Search all patterns and apply all functions to *output* of run *cmd_name*.
        """
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
    parser.add_pattern(attribute="attr", regex=r"(world)",
                       cmd_names="test", type=str)
    result = parser.parse(cmd_name="test", output="Hello world!")
    pprint.pprint(result)
