import questionary
import questionary.prompts.common
import shutil
import textwrap
from typing import Any, Callable, Dict, Optional, Union

STYLE_DISABLED = "fg:#858585 italic"

questionary.prompts.common.INDICATOR_SELECTED = "[🔪]"
questionary.prompts.common.INDICATOR_UNSELECTED = "[  ]"


class HelpText():
    def __init__(self,
                 key: str,
                 text: str,
                 print_if: Optional[Callable[[Dict[str,Any]], bool]] = None) -> None:
        self.key = key
        self.text = text
        self.print_if = print_if or (lambda _: True)

    def print(self):
        questionary.print(self.text)


class Question():
    def __init__(self,
                 key: str,
                 prompt_fn: Callable[..., Any],
                 default: Union[Any, Callable[[Dict[str,Any]], Any]] = None,
                 bottom_toolbar: Union[str, Callable[[Dict[str,Any]],str], None] = None,
                 convert_data_to_input: Optional[Callable[[Any], Any]] = None,
                 convert_input_to_data: Optional[Callable[[Any], Any]] = None,
                 ask_if: Optional[Callable[[Dict[str,Any]], bool]] = None,
                 **args: Any) -> None:
        self.key = key
        self.prompt_fn = prompt_fn
        self.default = default
        self.bottom_toolbar = bottom_toolbar
        self.convert_data_to_input = convert_data_to_input or (lambda x: x)
        self.convert_input_to_data = convert_input_to_data or (lambda x: x)
        self.ask_if = ask_if or (lambda _: True)
        self.args = args

    def _get_default(self, answers: Dict[str,Any]):
        if self.key in answers:
            default = answers[self.key]
        elif callable(self.default):
            default = self.default(answers)
        else:
            default = self.default
        if default is None:
            return None
        else:
            return self.convert_data_to_input(default)

    def _get_bottom_toolbar(self, answers: Dict[str,Any]) -> Optional[str]:
        if callable(self.bottom_toolbar):
            toolbar = self.bottom_toolbar(answers)
        else:
            toolbar = self.bottom_toolbar
        if toolbar is not None:
            toolbar = textwrap.fill(toolbar, width=_get_terminal_width())
        return toolbar

    def ask(self, answers: Dict[str,Any]):
        args = dict(self.args)
        default = self._get_default(answers)
        if isinstance(default, list) and "choices" in args:
            choices = args["choices"]
            for choice in choices:
                choice.checked = (choice.title in default)
        elif default is not None:
            args["default"] = default
        bottom_toolbar = self._get_bottom_toolbar(answers)
        if bottom_toolbar is not None:
            args["bottom_toolbar"] = bottom_toolbar
        prompt = self.prompt_fn(**args)
        raw = prompt.unsafe_ask()
        return self.convert_input_to_data(raw)


def _get_terminal_width():
    try:
        return shutil.get_terminal_size().columns
    except OSError:
        return 80

def print_separator():
    width = _get_terminal_width()
    questionary.print("-" * width, style=STYLE_DISABLED)

def run_interview(questions: list[Union[Question, HelpText]], preanswers: Dict[str, Any]):
    print("Starting Interview. Press Ctrl+C to cancel a question and go back to the previous question.\n")
    index = 0
    history = []
    answers = dict(preanswers)
    next_interrupt_exits = False
    try:
        while index < len(questions):
            question = questions[index]

            if isinstance(question, HelpText):
                help = question
                if help.print_if(answers):
                    help.print()
                index += 1
                continue

            if not question.ask_if(answers):
                index += 1
                continue
            try:
                answer = question.ask(answers)
            except KeyboardInterrupt:
                if next_interrupt_exits:
                    return None
                if history:
                    questionary.print(
                        "Cancelled. Going back to previous question.",
                        style=STYLE_DISABLED)
                    index = history.pop()
                else:
                    questionary.print(
                        "Already at first question, cannot go back further. "
                        "Press Ctrl+C again to exit.",
                        style=STYLE_DISABLED)
                    next_interrupt_exits = True
                print_separator()
                continue
            next_interrupt_exits = False
            answers[question.key] = answer
            history.append(index)
            index += 1
        return answers
    except EOFError:
        print("Aborting interview.")
        return None
