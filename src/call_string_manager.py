class CallStringManager:
    """Class for storing and handling planner execution commands."""

    def __init__(self, call_string):
        self.call_string = call_string
        self.indices = []
        self.call_string_list = self.call_string.split(" ")
        for index, arg in enumerate(self.call_string_list):
            if ".pddl" in arg:
                self.pddl_problem = True
                self.indices.append(index)
            elif ".sas" in arg:
                self.pddl_problem = False
                self.indices.append(index)
        if self.pddl_problem:
            assert len(self.indices) == 2
        else:
            assert len(self.indices) == 1

    def replace_pddl(self, domain_filename, problem_filename):
        assert self.pddl_problem
        self.call_string_list[self.indices[0]] = domain_filename
        self.call_string_list[self.indices[1]] = problem_filename
        self.call_string = " ".join(self.call_string_list)

    def replace_sas(self, sas_filename):
        assert not self.pddl_problem
        self.call_string_list[self.indices[0]] = sas_filename
        self.call_string = " ".join(self.call_string_list)
