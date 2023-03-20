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

Run OBS and VOICEVOX.

```
python talk.py `
    --obs_pass GKzsYMK574JexVLr `
    --chat_video_id U5uMBS4kBuY `
    --openai_api_key <API KEY>
```

When you write a comment in the youtube stream, zundamon will read your comment and answer.  
The subtitile will be updated if there is a Text source named "zundamon_zimaku" in OBS.