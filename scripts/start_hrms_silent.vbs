' Runs the Waitress server with no console window.
Set fso = CreateObject("Scripting.FileSystemObject")
backend = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName)) & "\backend"
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = backend
sh.Run """" & backend & "\venv\Scripts\waitress-serve.exe"" --listen=127.0.0.1:8888 --threads=8 config.wsgi:application", 0, False
