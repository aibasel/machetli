"""
This file is derived from ``parser.py`` of Lab (<https://lab.readthedocs.io>).

Our *_ContentParser* is basically the *_FileParser* from Lab, except
that it has an *initialize* function to define the content to be parsed
instead of the *load_file* function.

The *Parser* class itself is adapted so that a pattern or function is
added for each *cmd_name* instead of the *file*.
"""

from collections import defaultdict
import logging
import re

from machetli import tools


def _get_pattern_flags(s):
    flags = 0
    for char in s:
        try:
            flags |= getattr(re, char)
        except AttributeError:
            logging.critical(f"Unknown pattern flag: {char}")
    return flags


class _Pattern:
    def __init__(self, attribute, regex, required, type_, flags):
        self.attribute = attribute
        self.type_ = type_
        self.required = required
        self.group = 1

        flags = _get_pattern_flags(flags)
        self.regex = re.compile(regex, flags)

    def search(self, content, cmd_name):
        found_props = {}
        match = self.regex.search(content)
        if match:
            try:
                value = match.group(self.group)
            except IndexError:
                logging.error(
                    f"Attribute {self.attribute} not found for pattern "
                    f"{self} in content of command {cmd_name}."
                )
            else:
                value = self.type_(value)
                found_props[self.attribute] = value
        return found_props

    def __str__(self):
        return self.regex.pattern


class _ContentParser:
    """
    Private class that parses a given file according to the added patterns
    and functions.
    """

    def __init__(self):
        self.patterns = []
        self.functions = []

    def add_pattern(self, pattern):
        self.patterns.append(pattern)

    def add_function(self, function):
        self.functions.append(function)

    def search_patterns(self, content, cmd_name):
        assert content is not None
        found_props = {}
        for pattern in self.patterns:
            found_props.update(pattern.search(content, cmd_name))
        return found_props

    def apply_functions(self, props, content):
        assert content is not None
        for function in self.functions:
            function(content, props)


class Parser:
    """
    Parse stdout and stderr strings.
    """
    def __init__(self):
        tools.configure_logging()
        self.content_parsers = defaultdict(_ContentParser)

    def add_pattern(self, attribute, regex, cmd_names, type=int, flags=""):
        """
        Look for *regex* in stdout and stderr of the executed runs
        with names *cmd_names* and cast what is found in brackets to *type*.
        
        Store the parsing result of this pattern under the name
        *attribute* in the properties dictionary returned by
        :meth:`parse(cmd_name, content) <machetli.parser.Parser.parse>`.

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
        pattern = _Pattern(attribute, regex, required=False, type_=type,
                           flags=flags)
        for name in tools.make_list(cmd_names):
            self.content_parsers[name].add_pattern(pattern)

    def add_function(self, function, cmd_names):
        """
        Add *function* to parser which is called on the content strings
        of the executed runs *cmd_names*. *cmd_names* can be used for
        single arguments and for argument lists.

        Functions are applied **after** all patterns have been evaluated.

        The function is passed the content strings and the properties
        dictionary. It must manipulate the passed properties dictionary.
        The return value is ignored.

        Usage example:

        .. code-block:: python

            parser = Parser()

            def facts_tracker(content, props):
                props["translator_facts"] =
                    re.findall(r"Translator facts: (\d+)", content)

            parser.add_function(facts_tracker, ["amazing_run", "superb_run"])
        """
        for name in tools.make_list(cmd_names):
            self.content_parsers[name].add_function(function)

    def parse(self, cmd_name, content):
        """
        Search all patterns and apply all functions to *content* of run
        *cmd_name*.
        """
        self.props = dict()

        for name, content_parser in list(self.content_parsers.items()):
            if name == cmd_name:
                self.props.update(
                    content_parser.search_patterns(content, cmd_name))

        for name, content_parser in list(self.content_parsers.items()):
            if name == cmd_name:
                content_parser.apply_functions(self.props, content)

        return self.props


if __name__ == "__main__":
    import pprint
    parser = Parser()
    parser.add_pattern(attribute="attr", regex=r"(world)",
                       cmd_names="test", type=str)
    result = parser.parse(cmd_name="test", content="Hello world!")
    pprint.pprint(result)
