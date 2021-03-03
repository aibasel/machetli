from parserbase import ParserBase


class Parser(ParserBase):
    def parse_output_string(self, output_string) -> bool:
        cond1 = "caught signal 11 -- exiting" in output_string
        cond2 = "caught signal 6 -- exiting" in output_string
        return cond1 or cond2
