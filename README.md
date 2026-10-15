# Simple Impulse (H2), a Forza Horizon 2 Independent Trigger Haptics Mod

Hooks onto Azimuth's natural data output for controller vibrations and translates them using Microsoft's GameInput service to craft a .DLL that directly outputs impulse trigger outputs to a supported controller.

Current release is: `v1.0`

Supports Azimuth version: `v0.9.9`

## How to use
1. Launch **Forza Horizon 2** (via Azimuth).
2. Double-click `SimpleImpulseH2.exe`.
3. Drive and enjoy independent trigger haptics!

### Wary of unknown .exe and .dll files from the internet? Me too.
### You can build your own .dll and .exe from scratch using the scripts in this release.

## Building from Source (GPLv3)
All source code is available in the `source/` folder. This project is open-source under the GPLv3 license.

### Building `FH2TriggerBridge.dll`:
1. Open Visual Studio and create a new **Dynamic-Link Library (DLL)** project for C++.
2. Replace `dllmain.cpp` with the contents of `source/dllmain.cpp`.
3. Set configuration to **Release x64**.
4. Build the solution (`Ctrl + Shift + B`) to generate `FH2TriggerBridge.dll`.

### Building your own `SimpleImpulseH2.exe`:
1. Install Python (I recommend 3.12, make sure PATH is enabled)
2. Use PIP in powershell or command prompt to install pyinstaller: `pip install pyinstaller`
3. In the same folder where fh2_trigger.py exists, run pyintaller in powershell/command prompt: `pyinstaller --onefile --name SimpleImpulseH2 fh2_trigger.py`
4. Locate your own `SimpleImpulseH2.exe` file inside the dist folder generated and move to the root folder of source. Feel free to delete the .spec, dist, and build afterwards.
