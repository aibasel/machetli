Output install.gif

Require python

Set Shell "bash"
Set FontSize 16
Set Width 1000
Set Height 300

Env PS1 "> "

Hide
Type "rm -r .venv"
Enter@50ms
Type "pip cache purge"
Enter@50ms
Type "clear"
Enter@50ms

Show
Sleep 500ms
Type "python -m venv .venv"

Hide
Enter
Wait@15s />$/

Show
Sleep 1000ms
Type "source .venv/bin/activate"
Enter
Wait@20s /\(\.venv\) >$/

Sleep 1000ms
Type "pip install machetli"
Enter
Wait@20s /\(\.venv\) >$/

Sleep 5s
