# Life_of_Zundamon

OpenAIの無料枠が切れたら命を終えるずんだもんを作りたい

# Requirements

- OBS 28.1.2
- [obs-websocket (4.9.1)](https://github.com/obsproject/obs-websocket/releases)


# Setup (Powershell)

Python 3.8.10

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r .\requirements.txt
```