def get_questions():
    questions = [
        {
            "key_path": ["INPUT", "DOMAIN"],
            "prompt": "Please specify the domain file:"
        },
        {
            "key_path": ["INPUT", "PROBLEM"],
            "prompt": "Please specify the problem file:"
        },
        {
            "key_path": ["COMMAND_STRING"],
            "prompt": "How should the planner be executed? "
                      "Input the command line of your planner call, "
                      "using \"{planner}\" to represent the binary "
                      "and \"{domain}\"/\"{problem}\" to represent "
                      "the input files. For example {planner} {domain} "
                      "{problem} --search astar(lmcut())."
        }
    ]
    return questions


def get_placeholders():
    placeholders = {
        "planner": ["PLANNER"],
        "domain": ["INPUT", "DOMAIN"],
        "problem": ["INPUT", "PROBLEM"]
    }
    return placeholders
