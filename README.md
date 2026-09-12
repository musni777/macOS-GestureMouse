# HandMouse — Two-Hand Gesture Mouse for macOS

Control your Mac’s mouse pointer using your camera and hand gestures.

**Right hand moves and scrolls. Left hand clicks, double-clicks, and controls dragging.** HandMouse runs locally using Python, OpenCV, MediaPipe hand landmarks, and macOS mouse events.

> **தமிழில்:** வலது கையால் mouse pointer-ஐ நகர்த்தலாம், scroll செய்யலாம். இடது கையால் click செய்யலாம். இடது கையை முழுவதும் மூடினால் double-click ஆகும்.

This is an experimental desktop interaction project. It uses an existing pretrained hand detector and rule-based gesture logic; no custom AI training is required to run it.

## Contents

- [What can it do?](#what-can-it-do)
- [Requirements and compatibility](#requirements-and-compatibility)
- [Download from GitHub](#download-from-github)
- [Install and run from source](#install-and-run-from-source)
- [Camera and Accessibility permissions](#camera-and-accessibility-permissions)
- [Gesture controls](#gesture-controls)
- [How the code works](#how-the-code-works)
- [Settings and tuning](#settings-and-tuning)
- [Build a macOS app and DMG](#build-a-macos-app-and-dmg)
- [Troubleshooting](#troubleshooting)
- [Current limitations](#current-limitations)
- [Future development](#future-development)

## What can it do?

- Move the pointer continuously in two dimensions, including diagonal, curved, and circular paths.
- Smooth movement with a time-based exponential filter and a cursor speed limit.
- Separate pointing and clicking between two hands.
- Left-click, right-click, double-click, drag-and-drop, and scroll vertically.
- Pause using a right-hand fist and resume using an open right palm.
- Display hand landmarks, finger numbers, hand roles, and the current action.
- Release an active drag if tracking is lost.
- Run in a preview mode that detects gestures without controlling the mouse.

Possible uses include touch-free desktop experiments, computer-vision demonstrations, human–computer interaction learning, and prototyping alternative input methods. It has not been validated as an accessibility product or a full replacement for a physical mouse.

## Requirements and compatibility

| Item | Requirement / tested setup |
| --- | --- |
| Operating system | macOS; development and app testing used macOS 15.0 |
| Processor | Intel Mac (`x86_64`) for the installation/build recipe below |
| Python | Tested with Python 3.9.6 |
| Camera | Built-in MacBook camera or a compatible webcam |
| Permissions | Camera and Accessibility |
| Internet | Needed to download packages; normal operation is local once dependencies and model assets are available |

The pinned OpenCV wheel used here requires macOS 12 or later. That is a dependency minimum, **not a claim that every macOS 12+ machine has been tested**.

This source currently checks for macOS and uses Apple frameworks. Windows and Linux are not supported by this version. Apple Silicon has not been validated with this pinned setup; the build commands explicitly produce an Intel app, not a universal app.

### Technology stack

| Technology | Purpose |
| --- | --- |
| Python | Main application and gesture state machine |
| OpenCV | Camera capture, mirrored video, and preview window |
| MediaPipe Hands | Pretrained hand detection and 21 landmarks per hand |
| NumPy | Numerical dependency used by the vision stack |
| PyAutoGUI | Pointer position, clicks, scrolling, and fail-safe checks |
| Quartz / PyObjC | Native macOS drag and mouse-release events |
| `ctypes` + ApplicationServices | Check macOS Accessibility authorization |
| PyInstaller | Optional packaging into a standalone `.app` |
| `hdiutil` | Optional packaging of the app into a `.dmg` |

## Download from GitHub

1. Open this repository on GitHub.
2. Click **Code → Download ZIP**.
3. Extract the downloaded ZIP.
4. Rename the extracted project folder to **HandMouse**.
5. Move it to your **Desktop** so the commands below match your folder location.
6. Confirm that `hand_mouse.py` is directly inside that folder.

If you already have a different `Desktop/HandMouse` project, keep a backup or use a different location and adjust the `cd` commands. Do not overwrite your working project unintentionally.

The main files are:

| File | Purpose |
| --- | --- |
| `hand_mouse.py` | Complete current two-hand application |
| `README.md` | Setup, controls, code overview, packaging, and troubleshooting |
| `camera_test.py`, if included | Earlier camera-only test |
| `hand_test.py`, if included | Earlier hand-detection test |

The two test scripts are optional development examples. They are not required to run `hand_mouse.py`.

## Install and run from source

Run these commands in **Terminal**, one block at a time. Stop and inspect the error if a command fails.

### 1. Check your environment

```bash
cd ~/Desktop/HandMouse
python3 --version
uname -m
sw_vers -productVersion
```

The setup below was tested using Python 3.9.6 on Intel macOS. If your Python or processor differs, do not assume the same pinned binary wheels will be available. Use a compatible Intel Python environment or adapt and test the dependencies separately.

### 2. Create a project virtual environment

For a fresh download:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

If `.venv` already exists and works, just activate it:

```bash
source .venv/bin/activate
```

Your Terminal prompt should begin with `(.venv)`.

### 3. Install the libraries

```bash
python -m pip install --upgrade pip setuptools wheel
```

```bash
python -m pip install --no-compile --timeout 120 \
  "numpy==1.26.4" \
  "opencv-contrib-python==4.10.0.84" \
  "mediapipe==0.10.21" \
  "pyautogui==0.9.54" \
  "jax==0.4.30" \
  "jaxlib==0.4.30" \
  "pyobjc-core==11.1" \
  "pyobjc-framework-Cocoa==11.1" \
  "pyobjc-framework-Quartz==11.1"
```

Use `opencv-contrib-python` here; do not additionally install `opencv-python` into the same environment. They both provide the `cv2` module.

`--no-compile` avoids an installation-time bytecode compilation failure encountered in JAX’s experimental GPU code on Python 3.9. It does not make that experimental code Python 3.9-compatible. HandMouse does not use that GPU feature. JAX is included in this source environment because this MediaPipe release declares it as a dependency.

Packages already installed or cached can be reused. Initial downloads may take time, especially on a slow connection.

### 4. Verify installation

```bash
python -m pip check
```

```bash
python -c "import cv2, mediapipe as mp, numpy, pyautogui; print('OpenCV:', cv2.__version__); print('MediaPipe:', mp.__version__); print('Hand tracking:', hasattr(mp.solutions, 'hands')); print('All imports OK')"
```

Expected key messages:

```text
No broken requirements found.
Hand tracking: True
All imports OK
```

### 5. Run HandMouse

```bash
python hand_mouse.py
```

Grant the permissions described below. The app starts **paused**. Show an open **right** palm for about one second to begin.

> **தமிழில்:** முதலில் வலது உள்ளங்கையை camera-வுக்குக் காட்டுங்கள். பிறகு வலது ஆள்காட்டி விரலால் pointer-ஐ நகர்த்துங்கள்.

### Run again later

Every new Terminal session needs the virtual environment activated:

```bash
cd ~/Desktop/HandMouse
source .venv/bin/activate
python hand_mouse.py
```

### Preview without mouse actions

```bash
python hand_mouse.py --preview
```

Camera permission is still required. Preview mode bypasses the Accessibility check and does not move, click, or scroll the pointer.

### Select another camera

```bash
python hand_mouse.py --camera 1
```

The default camera index is `0`. Available camera indexes depend on the machine.

## Camera and Accessibility permissions

Open **System Settings → Privacy & Security**.

| Permission | Why it is needed |
| --- | --- |
| Camera | Read live video for hand detection |
| Accessibility | Send mouse movement and click events |

When running from Terminal, authorize **Terminal** or the host application macOS identifies. Quit and reopen it after changing permission, then reactivate `.venv`.

When running the packaged application, authorize **HandMouse.app** separately. Terminal’s permission does not necessarily authorize an app launched from Finder.

For Accessibility, use **+** to select the actual app you will run. For Camera, launch the app to request access and allow the prompt. Prefer installing the app into **Applications** before authorizing the distributed copy.

The current source prints a Terminal-oriented permission message. If this appears while running a packaged app, grant access to **HandMouse**, not just Terminal.

## Gesture controls

Keep both hands separated, within the frame, and with palms generally facing the camera. The preview is mirrored so movement feels natural. Read the role labels to check which hand was identified.

### Right hand: pointing, scrolling, and pause

| Gesture | Action |
| --- | --- |
| Open right palm for about 0.6 seconds | Start / resume |
| Extend and move the right index finger | Move the pointer in any 2D direction |
| Extend index + middle fingers; fold ring + little fingers; move vertically | Scroll |
| Close the right hand into a fist | Pause and release an active drag |

When resuming, keep the left hand relaxed and unpinched, or outside the frame. Movement and scrolling work without the left hand present.

### Left hand: clicks and dragging

| Gesture | Action |
| --- | --- |
| Touch thumb + index fingertips, then release | Left-click |
| Touch thumb + middle fingertips, then release | Right-click |
| Show an open left palm, then close the whole left hand for about 0.35 seconds | Double-click |
| Hold thumb + index pinch for at least 0.55 seconds | Start drag; move the right hand; release the left pinch to drop |

For a normal click, hold the pinch briefly—longer than the 0.08-second debounce but shorter than the drag threshold. Keep other fingers loosely extended so a pinch is not confused with a fist.

**Double-click is now a left fist gesture. Thumb + ring-finger pinch is no longer the double-click gesture.**

A held left fist produces only one double-click. Open the left palm again for at least 0.15 seconds before closing it for the next double-click. Allow roughly half a second for each gesture when learning.

If the left fist is formed during an active drag, the code releases the drag without issuing a double-click. Loss of either hand during dragging also releases the mouse button.

### Example: open a file

1. Use the right index finger to position the pointer over the file.
2. Open the left palm briefly.
3. Close the left hand into a fist and hold it for roughly half a second.
4. The app sends a left-button double-click at the pointer location.
5. Open the left hand again before another double-click.

### Keyboard controls and stopping

The video window must have keyboard focus for these keys:

| Key / action | Result |
| --- | --- |
| `Q` or `Esc` | Quit |
| `Space` | Toggle keyboard pause; after unlocking, show the right palm to resume |
| `L` | Toggle landmark drawing |
| Close the preview window | Quit |
| `Control + C` in the running Terminal | Stop the source program |
| Move the physical pointer to a screen corner with the trackpad | Trigger PyAutoGUI’s fail-safe when the next checked mouse action runs |

Use a right fist or remove your hands from the frame if you need to take over with the trackpad.

## How the code works

### Processing order

1. OpenCV reads a camera frame using the macOS AVFoundation backend.
2. The frame is mirrored and converted from BGR to RGB.
3. MediaPipe detects/tracks up to two hands and returns landmarks and handedness.
4. `select_hands()` assigns the detected hands to **Right** and **Left** roles.
5. Right index coordinates become the pointer target; right finger posture selects scrolling or pause.
6. Left fingertip distances and finger posture select clicks, dragging, or fist double-click.
7. `Controller` applies gesture timing, release rules, cooldowns, and movement smoothing.
8. `MacMouse` sends mouse events through PyAutoGUI or Quartz.
9. The preview displays the hand roles, landmarks, and current state.

MediaPipe’s pretrained detector processes camera images. The custom gesture rules operate on landmarks rather than a separately trained image classifier.

### Main code components

| Component in `hand_mouse.py` | Responsibility |
| --- | --- |
| Constants at the top | Gesture thresholds, smoothing, speed, camera margin, and frame-rate target |
| `clamp()` / `distance()` | Bound values and measure 2D distances |
| `finger_up()` | Estimate whether a finger is extended using joint geometry and wrist distance |
| `select_hands()` | Route hands by MediaPipe labels; reject uncertain or duplicate labels |
| `Controller.update()` | Interpret gestures and manage click, drag, scroll, and pause states |
| `Controller.move()` | Map coordinates, smooth movement, and apply a speed limit |
| `Controller.cancel()` / `missing()` | Cancel pending gestures and release an active drag |
| `MacMouse` | Native mouse actions and preview-mode suppression |
| `accessibility_trusted()` | Check Accessibility authorization through ApplicationServices |
| `main()` | Parse options, open camera, run the frame loop, and clean up |

### Coordinates and smoothing

Normal movement uses the right index fingertip’s `x` and `y` coordinates. A central camera region is mapped onto the primary display. Pointer motion is not limited to four directions.

The smoothing factor depends on elapsed time:

```python
alpha = 1 - math.exp(-dt / SMOOTH_TAU)
```

The controller approaches the target gradually, ignores very small changes, and limits travel per update. During dragging, movement uses relative changes in the right index position.

### Gesture reliability

- Pinch distances are divided by palm width so thresholds are less sensitive to camera distance.
- Separate pinch-on and pinch-off thresholds provide hysteresis.
- Pinch clicks happen on release; very brief pinches are ignored.
- The left fist needs a short hold and an open-palm rearm before another double-click.
- The pointer freezes during click selection to reduce target drift.
- Missing or ambiguous hand tracking cancels pending actions.
- Right-hand fist pause takes priority over click actions.

These measures reduce accidental gestures but do not eliminate all detection errors.

## Settings and tuning

Edit these constants near the top of `hand_mouse.py`, save, and restart. A packaged app must be rebuilt after source changes.

| Setting | Default | Meaning |
| --- | --- | --- |
| `PINCH_ON` | `0.28` | Pinch begins below this palm-normalized distance |
| `PINCH_OFF` | `0.43` | Pinch releases above this distance; keep above `PINCH_ON` |
| `DEBOUNCE` | `0.08` | Minimum pinch time for a click, in seconds |
| `DRAG_HOLD` | `0.55` | Hold time to start dragging |
| `FIST_HOLD` | `0.35` | Left fist hold time for double-click |
| `FIST_REARM` | `0.15` | Open left palm time to rearm double-click |
| `COOLDOWN` | `0.30` | Delay between click actions |
| `RESUME_HOLD` | `0.60` | Open right palm time to resume |
| `SCROLL_HOLD` | `0.18` | V-sign settling time before scrolling |
| `SCROLL_STEP` | `0.035` | Camera-height fraction per scroll step; larger means less sensitive |
| `SMOOTH_TAU` | `0.10` | Larger means smoother movement with more lag |
| `MAX_SPEED` | `1800.0` | Cursor speed cap in screen-coordinate units per second |
| `CAMERA_MARGIN` | `0.15` | Margin on each side of the mapped camera region |
| `FPS` | `24` | Processing-rate target, not a guaranteed measured frame rate |

The code requests a 640 × 480 camera stream, uses `model_complexity=0`, tracks at most two hands, and limits OpenCV to one thread. Actual CPU use, memory use, and responsiveness depend on the Mac and camera; no cross-device performance benchmark is claimed.

## Build a macOS app and DMG

Build on an Intel Mac using the working environment above. Python and required libraries are bundled into the app, so recipients do not need to install Python separately.

A `.dmg` is a disk image containing the app and an Applications shortcut. Renaming a `.py` file to `.dmg` does not create an application.

All project build outputs in this guide are placed under the HandMouse folder. Package-manager and OS caches may still use their normal system locations.

### 1. Install PyInstaller

Stop any running HandMouse instance first.

```bash
cd ~/Desktop/HandMouse
source .venv/bin/activate
python -m pip install --no-compile --timeout 120 "pyinstaller==6.16.0"
```

### 2. Build the app

```bash
python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name HandMouse \
  --osx-bundle-identifier com.musni.handmouse \
  --target-architecture x86_64 \
  --collect-data mediapipe \
  --collect-submodules mediapipe.python \
  --collect-submodules mediapipe.calculators \
  --collect-submodules mediapipe.framework \
  --hidden-import Quartz \
  --hidden-import Quartz.CoreGraphics \
  --hidden-import AppKit \
  --hidden-import Foundation \
  --exclude-module jax \
  --exclude-module jaxlib \
  --distpath ./dist \
  --workpath ./build \
  --specpath . \
  hand_mouse.py
```

The result is `dist/HandMouse.app`. The optional JAX runtime is excluded from this hand-tracking bundle; it remains installed in the source virtual environment. This packaging recipe was used successfully on the development Mac.

`--noconfirm` allows replacement of previous generated build output. Keep your editable source outside `dist` and `build`.

### 3. Add app metadata and the camera usage description

```bash
python - <<'PY'
import plistlib
from pathlib import Path

path = Path("dist/HandMouse.app/Contents/Info.plist")
with path.open("rb") as file:
    info = plistlib.load(file)

info.update({
    "CFBundleDisplayName": "HandMouse",
    "CFBundleShortVersionString": "1.0.0",
    "CFBundleVersion": "1.0.0",
    "NSCameraUsageDescription":
        "HandMouse uses the camera to detect hand gestures and control the mouse.",
    "NSHighResolutionCapable": True,
})

with path.open("wb") as file:
    plistlib.dump(info, file)
print("App settings updated.")
PY
```

### 4. Sign locally and verify

```bash
codesign --force --deep --sign - "dist/HandMouse.app"
codesign --verify --deep --strict --verbose=2 "dist/HandMouse.app"
```

This is an **ad-hoc signature**, not Apple Developer ID signing or notarization. Signature verification confirms signature integrity; it does not prove the app works or guarantee Gatekeeper acceptance on another Mac.

### 5. Test the app before packaging

```bash
open "dist/HandMouse.app"
```

Grant **HandMouse.app** Camera and Accessibility permission. Test movement, scrolling, clicks, fist double-click, drag release, pause, and quit.

Do not repeatedly use `open -n`: it starts additional instances, which may compete for the camera. See troubleshooting if the app exits or appears not to open.

### 6. Create the disk image

Close the app, then run:

```bash
mkdir -p dmg_contents
ditto "dist/HandMouse.app" "dmg_contents/HandMouse.app"
```

```bash
if [ ! -e "dmg_contents/Applications" ]; then
  ln -s /Applications "dmg_contents/Applications"
fi
```

```bash
hdiutil create \
  -volname "HandMouse" \
  -srcfolder "dmg_contents" \
  -format UDZO \
  -ov \
  "HandMouse.dmg"
```

```bash
hdiutil verify "HandMouse.dmg"
open -R "HandMouse.dmg"
```

Final output: **`Desktop/HandMouse/HandMouse.dmg`**. `-ov` replaces an existing DMG with that name. Use a clean staging folder when preparing a new release so removed files from older builds are not retained.

### Install the packaged app

1. Open `HandMouse.dmg`.
2. Drag **HandMouse.app** onto **Applications**.
3. Eject the disk image.
4. Open the app from Applications.
5. Grant Camera and Accessibility access to the installed app.
6. Reopen it if necessary and show the right palm to start.

This recipe produces an **Intel macOS app**. Test on a recipient’s compatible machine before claiming broader support. A downloaded, non-notarized app may be blocked or show a security warning. Developer ID signing and Apple notarization are separate distribution steps; do not disable system-wide security protections to distribute the app.

## Troubleshooting

### `python: command not found`

Activate the existing virtual environment:

```bash
cd ~/Desktop/HandMouse
source .venv/bin/activate
```

### `can't open file ... hand_mouse.py`

Check that the extracted source file is directly inside your current project folder:

```bash
pwd
ls -l hand_mouse.py
```

### JAX installation stops with `match self.layout` / `SyntaxError`

On the tested Python 3.9 setup, repair the partial JAX installation using cached downloads:

```bash
python -m pip install --no-compile --no-deps --force-reinstall --timeout 120 "jax==0.4.30"
```

Then rerun the main library installation command above with `--no-compile`, followed by the installation checks. Do not delete the whole environment as the first troubleshooting step.

### `AttributeError: AXIsProcessTrusted`

An older source version tried to access this function through Quartz. The current code uses `ctypes` with ApplicationServices instead. Update `hand_mouse.py` and rebuild if running an older packaged app.

### Camera access denied

Enable Camera access for the program actually launching HandMouse. Quit and reopen that program. Terminal and Finder-launched HandMouse may need separate permissions.

### Pointer does not move

- Check Accessibility permission for the correct application.
- The app starts paused: show the right open palm for about one second.
- Look at the preview status and hand-role labels.
- Confirm you did not start with `--preview`.
- Keep the left hand relaxed rather than holding a click gesture.

### Double-click does not happen

Use the **left fist**, not the old ring-finger pinch. Show an open left palm first, then close it for about half a second. A held fist does not repeat; reopen before the next double-click. Keep the right hand visible and the app unpaused.

### App builds successfully but does not appear to open

Run its actual executable to inspect output:

```bash
cd ~/Desktop/HandMouse
"./dist/HandMouse.app/Contents/MacOS/HandMouse" 2>&1 | tee app_error.txt
```

A Finder launch may have different permissions. To capture that launch, first close existing instances, then run this **once**:

```bash
open --stdout "$PWD/finder_output.txt" \
  --stderr "$PWD/finder_error.txt" \
  "dist/HandMouse.app"
```

After a few seconds:

```bash
cat finder_output.txt finder_error.txt
```

The application must not already be running if you want to diagnose a fresh launch this way.

### `Camera frame lost. Stopping.`

The current code stops if a camera frame cannot be read. Close other camera applications and duplicate HandMouse instances.

To stop all packaged processes named HandMouse:

```bash
pkill -x HandMouse
```

Also stop any source camera test or `python hand_mouse.py` with `Control + C` in its Terminal. Then launch one copy:

```bash
open "dist/HandMouse.app"
```

If the frame error continues with only one instance, check camera permission, camera availability, and the selected camera index. Automatic camera reconnection is not implemented yet.

### Informational messages

`Matplotlib is building the font cache` can appear during initialization. MediaPipe messages about XNNPACK, feedback tensors, or landmark projection are not by themselves proof that the app failed. Look for an actual traceback, permission message, or frame-read failure.

### Hand detection is inconsistent

Use good lighting, avoid strong backlighting, keep hands apart, and face palms toward the camera. Avoid crossing or overlapping hands. The code rejects low-confidence hand labels and hands that appear too small; move closer if necessary.

Adding colored dots to the preview only helps visualize already-detected landmarks. It does not improve the underlying detector.

## Privacy and local processing

The current application processes camera frames locally and does not implement video recording or upload camera frames to a server. It has no cloud AI API requirement. Dependency installation and initial asset availability are separate from normal local operation.

## Current limitations

- Only the primary display is mapped.
- macOS-specific implementation; no native Windows/Linux support.
- Pinned setup and Intel app build have limited machine testing.
- Fingers, handedness, and fists can be misclassified, especially with occlusion or poor lighting.
- Holding hands in the air may become tiring; retain a trackpad or physical mouse for normal use.
- Camera frame-read failure currently stops the program.
- No automatic single-instance lock, auto-update system, calibration UI, or custom gesture editor.
- No eye-blink clicking, custom-trained gesture classifier, or user identity recognition.
- No claim of measured low CPU/RAM usage across all machines.

## Future development

These are proposed improvements, **not features already implemented**:

1. **Personal calibration:** adjust pinch thresholds, active camera area, smoothing, and scroll sensitivity per user.
2. **Reliability:** prevent duplicate app instances, retry temporary camera failures, and show permission guidance inside the app.
3. **Better hand tracking:** improve handling of overlapping hands, handedness uncertainty, and fist transitions.
4. **Flexible controls:** allow left-handed layouts and customizable gesture mappings.
5. **Desktop integration:** menu-bar controls, a settings window, multiple-monitor support, and an app icon.
6. **Broader compatibility:** validate Apple Silicon builds and create native backends for other operating systems.
7. **Small gesture classifier:** collect consenting users’ landmark examples and compare a tiny learned classifier against the current rules.
8. **Alternative inputs:** investigate deliberate eye/wink gestures while distinguishing them from natural blinks.
9. **Distribution:** reproducible builds, release notes, Developer ID signing, and notarization.

### Optional future AI training

MediaPipe provides 21 landmarks × 3 coordinates = **63 values per hand**. Two hands can provide 126 coordinate values, plus hand-presence indicators if needed. A future dataset should normalize hand size/orientation and label examples consistently.

A possible per-hand experiment is a small classifier with 63 inputs, 64 and 32 hidden units, and gesture-class outputs. Training could be done in Kaggle and evaluated on held-out sessions/users before export to ONNX or LiteRT/TFLite.

This is a research direction. It is not needed for the current app and is not guaranteed to improve on the rule-based controls without useful data and evaluation.

## Keeping the GitHub repository clean

Upload source and documentation. Do not upload your virtual environment, app bundles, DMGs, build folders, generated logs, or personal recordings into the source repository.

Typical `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
.DS_Store
build/
dist/
dmg_contents/
release/
.packaging/
*.app/
*.dmg
*.log
app_error.txt
finder_output.txt
finder_error.txt
```

If you later share a distributable DMG through GitHub, use a Release asset rather than mixing the binary into the source tree.

## Documentation references

- [MediaPipe Hands](https://chuoling.github.io/mediapipe/solutions/hands.html)
- [OpenCV camera/video tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html)
- [PyAutoGUI mouse controls](https://pyautogui.readthedocs.io/en/latest/mouse.html)
- [PyAutoGUI fail-safes](https://pyautogui.readthedocs.io/en/latest/index.html#fail-safes)
- [PyInstaller documentation](https://pyinstaller.org/en/v6.16.0/)
- [Apple: camera access on Mac](https://support.apple.com/guide/mac-help/control-access-to-the-camera-mchlf6d108da/mac)
