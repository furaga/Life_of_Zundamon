# Life_of_Zundamon

OpenAIの無料枠が切れたら命を終えるずんだもんを作りたい

# Requirements

- OBS 28.1.2
- [obs-websocket (4.9.1)](https://github.com/obsproject/obs-websocket/releases)
- VOICEVOX 0.14.5

# Setup (Powershell)

Python 3.8.10

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r .\requirements.txt
```

# Usage

(OBSの画面構成については割愛)

Run OBS and VOICEVOX. Then,

```
$env:OPENAI_API_KEY = <YOUR OPENAI API KEY>
python talk.py `
    --obs_pass <obsstream password>
    --chat_video_id <YOUTUBE STREAM'S VIDEO ID> `
```

When you write a comment in the youtube stream, zundamon will read your comment and answer.  
The subtitile in OBS, a Text source named "zundamon_zimaku", will be updated.