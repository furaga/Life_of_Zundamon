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

Download VOICEVOX CORE wheel from [here](https://github.com/VOICEVOX/voicevox_core/releases/tag/0.14.1)

```powershell
python -m pip install wheel/voicevox_core-0.14.1+cuda-cp38-abi3-win_amd64.whl
Invoke-WebRequest https://github.com/VOICEVOX/voicevox_core/releases/latest/download/download-windows-x64.exe -OutFile ./download.exe
./download.exe
```
