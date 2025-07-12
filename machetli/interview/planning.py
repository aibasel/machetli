from datetime import datetime
from importlib import resources
from pathlib import Path
import re
import shutil
import stat
import sys
from typing import Union

from Cheetah.Template import Template
import questionary
from questionary import Style

from machetli import sas, pddl
from machetli.pddl.files import find_domain_path
from machetli.templates import interview as templates
from machetli.interview.questions import Question, HelpText


INPUT_TYPE_PDDL = "PDDL"
INPUT_TYPE_SAS = "SAS"
INPUT_TYPE_PDDL_THEN_SAS = "PDDL then SAS"
EVALUATOR_TYPE_EXIT_CODE = "exit code"
EVALUATOR_TYPE_OUTPUT = "output"
EVALUATOR_TYPE_EXIT_CODE_DIFF = "exit code difference"
EVALUATOR_TYPE_OUTPUT_DIFF = "output difference"

NON_REVERSED_SELECTION = Style([('selected', 'noreverse')])

def get_questions() -> list[Union[Question, HelpText]]:
    return [
        Question(
            key="input_type",
            prompt_fn=questionary.select,
            message="What kind of input do you want Machetli to simplify?",
            choices=[
                questionary.Choice("PDDL domain and problem files", INPUT_TYPE_PDDL),
                questionary.Choice("A SAS^+ file", INPUT_TYPE_SAS),
                questionary.Choice("Start with PDDL files, simplify as much as possible, "
                       "then translate the result to SAS^+ and continue simplifying",
                       INPUT_TYPE_PDDL_THEN_SAS),
            ],
            use_arrow_keys=True,
            use_shortcuts=True,
        ),
        Question(
            key="problem",
            prompt_fn=questionary.path,
            ask_if=_need_pddl_input,
            message="Please specify the problem file:",
            validate=_validate_existing_file,
        ),
        Question(
            key="domain",
            prompt_fn=questionary.path,
            ask_if=_need_pddl_input,
            message="Please specify the domain file:",
            default=_detect_domain,
            validate=_validate_existing_file,
        ),
        Question(
            key="sas_task",
            prompt_fn=questionary.path,
            ask_if=_need_sas_input,
            message="Please specify the SAS^+ file:",
            validate=_validate_existing_file,
        ),
        Question(
            key="evaluator_type",
            prompt_fn=questionary.select,
            message="Which behavior do you observe?",
            choices=[
                questionary.Choice(
                    title="My planner returns an unexpected exit code.",
                    value=EVALUATOR_TYPE_EXIT_CODE,
                    description="Machetli will run the planner and check the exit code."),
                questionary.Choice(
                    title="My planner prints a line that it shouldn't.",
                    value=EVALUATOR_TYPE_OUTPUT,
                    description="Machetli will run the planner and check whether a "
                    "given pattern occurs in the output of the run."),
                questionary.Choice(
                    title="The exit code of my planner differs from a reference planner.",
                    value=EVALUATOR_TYPE_EXIT_CODE_DIFF,
                    description="Machetli will run both planners and compare their exit codes."),
                questionary.Choice(
                    title="The output of my planner differs from a reference planner.",
                    value=EVALUATOR_TYPE_OUTPUT_DIFF,
                    description="Machetli will run both planners, parse a value from their output "
                    "and compare the parsed values."),
            ],
            use_arrow_keys=True,
            use_shortcuts=True,
            show_description=True,
        ),
        Question(
            key="planner",
            prompt_fn=questionary.path,
            message="Please specify the path to your planner:",
            validate=_validate_non_empty,
        ),
        Question(
            key="planner_cmd",
            prompt_fn=questionary.text,
            message="How should the planner be executed?",
            bottom_toolbar=_get_planner_command_instruction,
            validate=_validate_non_empty,
            convert_data_to_input=_bash_untokenize,
            convert_input_to_data=_bash_tokenize,
        ),
        Question(
            key="sas_planner_cmd",
            prompt_fn=questionary.text,
            ask_if=_need_pddl_and_sas_planners,
            message="How should the planner be executed on SAS^+ files?",
            default=lambda answers: _detect_sas_cmd_from_pddl_cmd(answers["planner_cmd"]),
            # Pretend the input type is SAS^+ for this question.
            bottom_toolbar=_get_planner_command_instruction(
                            {"input_type": INPUT_TYPE_SAS}),
            validate=_validate_non_empty,
            convert_data_to_input=_bash_untokenize,
            convert_input_to_data=_bash_tokenize,
        ),
        HelpText(
            key="translatorhelp",
            text="To be able to translate PDDL files into SAS^+, Machetli "
                "needs access to a translator.",
            print_if=_need_pddl_and_sas_planners,
        ),
        Question(
            key="translator",
            prompt_fn=questionary.path,
            ask_if=_need_pddl_and_sas_planners,
            message="Please specify the path to translate.py",
            default=_detect_translator,
            validate=_validate_non_empty,
        ),
        Question(
            key="reference_planner",
            prompt_fn=questionary.path,
            ask_if=_need_reference_planner,
            message="Please specify the path to the planner that Machetli "
                "should compare to. We call this the reference planner:",
            default=lambda answers: answers["planner"],
            validate=_validate_non_empty,
        ),
        Question(
            key="reference_planner_cmd",
            prompt_fn=questionary.text,
            ask_if=_need_reference_planner,
            message="How should the reference planner be executed?",
            default=lambda answers: answers["planner_cmd"],
            bottom_toolbar=_get_planner_command_instruction,
            validate=_validate_non_empty,
            convert_data_to_input=_bash_untokenize,
            convert_input_to_data=_bash_tokenize,
        ),
        Question(
            key="sas_reference_planner_cmd",
            prompt_fn=questionary.text,
            ask_if=_need_pddl_and_sas_reference_planners,
            message="How should the reference planner be executed on SAS^+ files?",
            default=lambda answers: _detect_sas_cmd_from_pddl_cmd(answers["reference_planner_cmd"]),
            # pretend the input type is SAS^+ for this question.
            bottom_toolbar=_get_planner_command_instruction(
                            {"input_type": INPUT_TYPE_SAS}),
            validate=_validate_non_empty,
            convert_data_to_input=_bash_untokenize,
            convert_input_to_data=_bash_tokenize,
        ),
        HelpText(
            key="limits_help",
            text="You should limit resources so the individual runs do not run "
                "forever or exhaust memory of the host.",
        ),
        Question(
            key="time_limit",
            prompt_fn=questionary.text,
            message="Time limit:",
            default = "60s",
            bottom_toolbar="Allowed suffixes: s (seconds), m (minutes), h (hours)"
                "Integers without suffix are interpreted as seconds.",
            validate=_validate_time_limit,
        ),
        Question(
            key="memory_limit",
            prompt_fn=questionary.text,
            message="Memory limit:",
            default = "2G",
            bottom_toolbar="Allowed suffixes: K (KiB), M (MiB), G (GiB). "
                "Integers without suffix are interpreted as MiB.",
            validate=_validate_memory_limit,
        ),
        HelpText(
            key="parsed_value_help",
            text="You said that Machetli should look for a value in the planner's output. "
                 "We will now ask details about this value.",
            print_if=_need_parsed_value,
        ),
        Question(
            key="parsed_value_source",
            prompt_fn=questionary.text,
            message="Where should Machetli parse the value from?",
            ask_if=_need_parsed_value,
            default = "stdout",
            bottom_toolbar=
                "Use 'stdout', 'stderr' or the path to a file generated by the planner run, "
                "relative to the working directory."
            ,
            validate=_validate_non_empty,
        ),
        Question(
            key="parsed_value_regex",
            prompt_fn=questionary.text,
            ask_if=_need_parsed_value,
            message="Please write a regular expression matching the line you want to parse.",
            bottom_toolbar=
                "The first match of the line will be used and the first group in the regex "
                "will be used to parse the value. For example use 'Total time: (\\d+)s' to "
                "parse the number of seconds after 'Total time:'.",
            validate=_validate_regex,
        ),
        Question(
            key="parsed_value_type",
            prompt_fn=questionary.select,
            ask_if=_need_parsed_value,
            message="Should Machetli cast the value in a particular type before comparing it?",
            choices=[
                questionary.Choice("String", "str"),
                questionary.Choice("Integer", "int"),
                questionary.Choice("Float", "float"),
            ],
        ),
        Question(
            key="parsed_value_evaluation",
            prompt_fn=questionary.text,
            ask_if=_need_single_parsed_value,
            message="How can Machetli detect if the observed behavior is present?",
            bottom_toolbar=
                "Write a Python expression involving the variable 'value' "
                "that evaluates to True if the behavior is present, e.g. "
                "'value > 5'. In cases where the values cannot be found in "
                "the output, Machetli assumes that the behavior does not occur.",
            default="True",
            validate=_validate_non_empty,
        ),
        Question(
            key="parsed_value_evaluation",
            prompt_fn=questionary.text,
            ask_if=_need_multiple_parsed_values,
            message="How can Machetli detect if the observed behavior is present?",
            bottom_toolbar=
                "Write a Python expression involving the variables 'value' "
                "and 'reference_value' that evaluates to True if the behavior "
                "is present, e.g. 'value > reference_value'. In cases where "
                "one of the values cannot be found in the output, Machetli "
                "assumes that the behavior does not occur.",
            default="value != reference_value",
            validate=_validate_non_empty,
        ),
        Question(
            key="exit_code_evaluation",
            prompt_fn=questionary.text,
            ask_if=_need_single_exit_code,
            message="How can Machetli detect if the observed behavior is present?",
            bottom_toolbar=
                "Write a Python expression involving the variable 'exit_code' "
                "that evaluates to True if the behavior is present, e.g. "
                "'exit_code == 23'.",
            default="exit_code != 0",
            validate=_validate_non_empty,
        ),
        Question(
            key="exit_code_evaluation",
            prompt_fn=questionary.text,
            ask_if=_need_multiple_exit_codes,
            message="How can Machetli detect if the observed behavior is present?",
            bottom_toolbar=
                "Write a Python expression involving the variables 'exit_code' "
                "and 'reference_exit_code' that evaluates to True if the behavior "
                "is present.",
            default="exit_code != reference_exit_code",
            validate=_validate_non_empty,
        ),
        Question(
            key="pddl_generators",
            prompt_fn=questionary.checkbox,
            ask_if=_need_pddl_generators,
            message="When simplifying PDDL files, which changes should Machetli try?",
            choices=[
                questionary.Choice(key, checked=True, description=generator().get_description())
                for key, generator in pddl.GENERATORS.items()
            ],
            validate=_validate_at_least_one,
            show_description=True,
            style=NON_REVERSED_SELECTION,
        ),
        Question(
            key="sas_generators",
            prompt_fn=questionary.checkbox,
            ask_if=_need_sas_generators,
            message="When simplifying SAS^+ files, which changes should Machetli try?",
            choices=[
                questionary.Choice(key, checked=True, description=generator().get_description())
                for key, generator in sas.GENERATORS.items()
            ],
            validate=_validate_at_least_one,
            show_description=True,
            style=NON_REVERSED_SELECTION,
        ),
        Question(
            key="script_location",
            prompt_fn=questionary.path,
            message="Where should Machetli store the generated scripts?",
            default="machetli_" + datetime.now().strftime("%Y-%m-%d_%H-%M"),
        ),
        Question(
            key="overwrite_script_location",
            prompt_fn=questionary.select,
            ask_if=lambda answers: Path(answers["script_location"]).expanduser().exists(),
            message="This directory already exists. (Press Ctrl+c to select a different loction)",
            choices=[
                questionary.Choice("Yes, overwrite the directory", True),
                questionary.Choice("No, abort the interview (scripts will not be written to disk)", False)
            ],
        ),
    ]


def _fill_template(template_name: str, config, path: Path, executable=False):
    template_src = resources.read_text(templates, template_name)
    content = str(Template(template_src, [config]))
    path.write_text(content)
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)


def generate_files(config):
    script_path = Path(config["script_location"])

    try:
        _fill_template("run.py.tmpl", config, script_path / "run.py", executable=True)
        if config["input_type"] in [INPUT_TYPE_PDDL, INPUT_TYPE_SAS]:
            _fill_template("evaluator.py.tmpl", config, script_path / "evaluator.py", executable=True)
        else:
            config["input_type"] = INPUT_TYPE_PDDL
            _fill_template("evaluator.py.tmpl", config, script_path / "pddl_evaluator.py", executable=True)
            config["input_type"] = INPUT_TYPE_SAS
            config["planner_cmd"] = config["sas_planner_cmd"]
            if _need_reference_planner(config):
                config["reference_planner_cmd"] = config["sas_reference_planner_cmd"]
            _fill_template("evaluator.py.tmpl", config, script_path / "sas_evaluator.py", executable=True)
        if "problem" in config:
            shutil.copy(Path(config["problem"]).expanduser(), script_path / "initial-problem.pddl")
        if "domain" in config:
            shutil.copy(Path(config["domain"]).expanduser(), script_path / "initial-domain.pddl")
        if "sas_task" in config:
            shutil.copy(Path(config["sas_task"]).expanduser(), script_path / "initial-task.sas")
    except OSError as e:
        print(f"Error copying file: {e}")
        sys.exit(1)

    executable = str(script_path / "run.py")
    if script_path.is_absolute() or executable.startswith("./") or executable.startswith("../"):
        return executable
    return "./" + executable


def _need_pddl_input(answers):
    return answers["input_type"] in [INPUT_TYPE_PDDL, INPUT_TYPE_PDDL_THEN_SAS]

def _need_sas_input(answers):
    return answers["input_type"] in [INPUT_TYPE_SAS]

def _need_pddl_and_sas_planners(answers):
    return answers["input_type"] in [INPUT_TYPE_PDDL_THEN_SAS]

def _need_reference_planner(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_EXIT_CODE_DIFF, EVALUATOR_TYPE_OUTPUT_DIFF]

def _need_pddl_and_sas_reference_planners(answers):
    return _need_pddl_and_sas_planners(answers) and _need_reference_planner(answers)

def _need_parsed_value(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_OUTPUT, EVALUATOR_TYPE_OUTPUT_DIFF]

def _need_single_parsed_value(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_OUTPUT]

def _need_multiple_parsed_values(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_OUTPUT_DIFF]

def _need_single_exit_code(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_EXIT_CODE]

def _need_multiple_exit_codes(answers):
    return answers["evaluator_type"] in [EVALUATOR_TYPE_EXIT_CODE_DIFF]

def _need_pddl_generators(answers):
    return answers["input_type"] in [INPUT_TYPE_PDDL, INPUT_TYPE_PDDL_THEN_SAS]

def _need_sas_generators(answers):
    return answers["input_type"] in [INPUT_TYPE_SAS, INPUT_TYPE_PDDL_THEN_SAS]

def _validate_non_empty(text):
    if len(text) > 0:
        return True
    else:
        return "Please enter a value"
    
def _validate_time_limit(text):
    if re.fullmatch(r"\d+\s*[smh]?", text):
        return True
    else:
        return "Please specify the time limit as an integer optionally followed by 's', 'm', or 'h'."

def _validate_memory_limit(text):
    if re.fullmatch(r"\d+\s*[kKmMgG]?", text):
        return True
    else:
        return "Please specify the memory limit as an integer optionally followed by 'K', 'M', or 'G'."

def _validate_at_least_one(values):
    if values:
        return True
    else:
        return "Please select at least one option"

def _validate_existing_file(text):
    if Path(text).expanduser().is_file():
        return True
    else:
        return f"File '{text}' not found."

def _validate_regex(text):
    if not text:
        return "Please enter a value"
    try:
        re.compile(text)
        return True
    except re.error as e:
        return str(e)


def _detect_domain(answers):
    problem = answers["problem"]
    problem_path = Path(problem).expanduser()
    default = problem_path.parent / "domain.pddl"
    return str(find_domain_path(problem_path) or default)

def _detect_translator(answers):
    default = "translate.py"
    planner_dir = Path(answers["planner"]).expanduser().parent
    candidates = [
        planner_dir / "builds" / "release" / "bin" / "translate" / "translate.py",
        planner_dir / "builds" / "debug" / "bin" / "translate" / "translate.py",
        planner_dir / "src" / "translate" / "translate.py",
        planner_dir / "translate" / "translate.py",
        planner_dir.parent.parent.parent / "src" / "translate" / "translate.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return default

def _detect_sas_cmd_from_pddl_cmd(pddl_cmd):
    cmd = []
    for part in pddl_cmd:
        if part == "{problem}":
            cmd.append("{task}")
        elif part == "{domain}":
            continue
        else:
            cmd.append(part)
    return cmd

def _get_planner_command_instruction(answers):
    if _need_pddl_input(answers):
        input_help = " and {domain}/{problem} to represent the input files"
        example = "{planner} {domain} {problem} --search \"astar(lmcut())\""
    elif _need_sas_input(answers):
        input_help = " and {task} to represent the input file"
        example = "{planner} {task} --search \"astar(lmcut())\""
    else:
        assert False
    return ("Input the command line of your planner call, using {planner} to represent\n"
        f"the planner{input_help}.\n"
        "Use \"\" to group arguments as you would on a shell.\n"
        f"For example: {example}.")

def _bash_tokenize(value):
    result = []
    i = 0
    length = len(value)

    def parse_word():
        nonlocal i
        word = []
        in_quotes = False
        escape = False
        while i < length:
            c = value[i]
            if escape:
                word.append(c)
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_quotes = not in_quotes
            elif c.isspace() and not in_quotes:
                break
            else:
                word.append(c)
            i += 1
        return "".join(word)

    while i < length:
        # Skip leading whitespace.
        while i < length and value[i].isspace():
            i += 1
        if i < length:
            result.append(parse_word())
    return result

def _bash_untokenize(cmd):
    parts = []
    for part in cmd:
        part = part.replace("\"", "\\\"")
        if " " in part:
            part = f"\"{part}\""
        parts.append(part)
    return " ".join(parts)
