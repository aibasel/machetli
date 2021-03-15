

def run_commands(state, parsers):
    if not isinstance(parsers, list):
        parsers = [parsers]
    results = {}
    for cmd_name, cmd in list(state["call_strings"].items()):
        output = subprocess.run(cmd,
                                text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT).stdout

        results[cmd_name] = {}
        for parser in parsers:
            results[cmd_name].update(parser.parse(cmd_name, output))

    return results

    
def run_pddl_tasks():
    


class Evaluator():
    def evaluate(self, state):
        pass
