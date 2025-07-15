Output interview.gif

Require python


Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 500

Env PS1 "> "

Hide
Type "source .venv/bin/activate"
Enter
Wait
Type "clear"
Enter
Sleep 100ms

Show
Type "machetli"
Sleep 100ms
Enter
Sleep 1s
Down
Sleep 1s
Type "1"
Sleep 1s
Enter
Sleep 1s
Type "path/to/large-problem.pddl"
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s
Down
Sleep 1s
Up
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s
Type "path/to/bugged-planner/"
Sleep 100ms
Tab
Down 2
Sleep 500ms
Enter
Sleep 500ms
Enter
Sleep 1s
Type '{planner} {domain} {problem} --search "astar(lmcut())"'
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 1s
Backspace 4
Type "== 30"
Sleep 2s
Enter
Sleep 1s
Type " "
Down
Sleep 500ms
Type " "
Sleep 1s
Type "a"
Sleep 1.5s
Enter
Sleep 1s
Backspace 16
Type "scripts"
Sleep 100ms
Enter
Sleep 2s
Type "./machetli_scripts/run.py"
Sleep 100ms
Enter
Wait@30s
Sleep 1s
Type "cat machetli_scripts/small-problem.pddl"
Sleep 100ms
Enter
Sleep 1s
Type "cat machetli_scripts/small-domain.pddl"
Sleep 100ms
Enter

Sleep 5s