#!/usr/bin/env python3
"""HandMouse V2: two-hand control for Intel macOS / Python 3.9.
Run: python hand_mouse.py; detection only: python hand_mouse.py --preview
RIGHT hand: index moves cursor; V sign scrolls; fist pauses; open palm resumes.
LEFT hand: thumb/index release clicks, hold 0.55s then move RIGHT hand to drag;
thumb/middle release right-clicks; close LEFT fist for 0.35s to double-click.
Open LEFT palm for 0.15s to rearm; holding fist never repeats.
Keep hands apart and palms facing the camera. Left hand can leave the frame
while moving/scrolling. Losing either hand during drag releases the button.
Q/Esc: quit; Space: keyboard pause; L: landmarks (video window focused).
Starts paused. Primary display only. No eye/blink control in this version.
"""
import argparse
import ctypes
import math
import sys
import time

PINCH_ON = 0.28                 # Distance / palm width
PINCH_OFF = 0.43                # Hysteresis prevents repeated clicks
DEBOUNCE = 0.08
DRAG_HOLD = 0.55
FIST_HOLD = 0.35
FIST_REARM = 0.15
COOLDOWN = 0.30
RESUME_HOLD = 0.60
SCROLL_HOLD = 0.18
SCROLL_STEP = 0.035             # Fraction of camera height / wheel step
SMOOTH_TAU = 0.10               # Higher = smoother, more lag
MAX_SPEED = 1800.0             # Screen pixels per second
CAMERA_MARGIN = 0.15
FPS = 24


def clamp(value, low, high):
    return max(low, min(high, value))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def finger_up(points, tip):
    # Joint angle and distance to wrist: less orientation-dependent than y only.
    mcp, pip, end = points[tip - 3], points[tip - 2], points[tip]
    a = (mcp[0] - pip[0], mcp[1] - pip[1])
    b = (end[0] - pip[0], end[1] - pip[1])
    denominator = math.hypot(*a) * math.hypot(*b)
    cosine = (a[0] * b[0] + a[1] * b[1]) / max(denominator, 1e-6)
    return cosine < -0.65 and distance(end, points[0]) > 1.12 * distance(pip, points[0])


class Controller:
    """Gesture state machine; mouse backend is injected for offline tests."""
    def __init__(self, mouse):
        self.mouse = mouse
        self.paused = True
        self.keyboard_pause = False
        self.mode = None
        self.started = 0.0
        self.dragging = False
        self.cooldown_until = 0.0
        self.open_since = None
        self.scroll_since = None
        self.scroll_y = None
        self.neutral_since = None
        self.armed = False
        self.last_time = None
        self.cursor = None
        self.previous_target = None
        self.left_fist_since = None
        self.left_open_since = None
        self.double_ready = False
        self.label = 'PAUSED - show open palm'

    def cancel(self):
        self.left_fist_since = None
        self.left_open_since = None
        self.double_ready = False
        if self.dragging:
            self.mouse.release()
        self.dragging = False
        self.mode = None
        self.scroll_since = None
        self.scroll_y = None
        self.armed = False
        self.neutral_since = None
        self.cursor = None
        self.previous_target = None

    def missing(self):
        self.cancel()
        self.open_since = None
        self.label = 'NO HAND - control stopped'

    def toggle(self):
        self.cancel()
        self.keyboard_pause = not self.keyboard_pause
        self.paused = True
        self.open_since = None
        self.label = 'KEYBOARD PAUSE' if self.keyboard_pause else 'Show open palm to resume'

    def move(self, target, dt, relative=False):
        width, height = self.mouse.size
        tx = clamp((target[0] - CAMERA_MARGIN) / (1 - 2 * CAMERA_MARGIN), 0, 1)
        ty = clamp((target[1] - CAMERA_MARGIN) / (1 - 2 * CAMERA_MARGIN), 0, 1)
        target_px = (2 + tx * (width - 5), 2 + ty * (height - 5))
        if self.cursor is None:
            self.cursor = tuple(self.mouse.position())
        if relative:
            old = self.previous_target or target_px
            desired = (self.cursor[0] + target_px[0] - old[0],
                       self.cursor[1] + target_px[1] - old[1])
        else:
            desired = target_px
        self.previous_target = target_px
        alpha = 1 - math.exp(-dt / SMOOTH_TAU)
        dx, dy = ((desired[i] - self.cursor[i]) * alpha for i in (0, 1))
        length = math.hypot(dx, dy)
        if length < 0.7:
            return
        scale = min(1, MAX_SPEED * dt / max(length, 1e-6))
        self.cursor = (clamp(self.cursor[0] + dx * scale, 2, width - 3),
                       clamp(self.cursor[1] + dy * scale, 2, height - 3))
        self.mouse.move(*self.cursor, dragging=self.dragging)

    def update(self, now, target, index_pinch, middle_pinch, extended, click_available=True, left_closed=False, left_open=False):
        dt = clamp(now - self.last_time, 0.001, 0.08) if self.last_time is not None else 1 / FPS
        self.last_time = now
        if not click_available:
            # A lost click hand is a cancellation, never a pinch release/click.
            if self.mode or self.dragging:
                self.cancel()
            self.armed = False
            self.neutral_since = None
            self.left_fist_since = None
            self.left_open_since = None
            self.double_ready = False
            left_closed = left_open = False
            index_pinch = middle_pinch = 1.0
        ratios = {'left': index_pinch, 'right': middle_pinch}
        fist = not any(extended)
        open_hand = all(extended) and min(ratios.values()) > PINCH_OFF
        if fist or self.keyboard_pause:
            self.cancel()
            self.paused = True
            self.open_since = None
            self.label = 'KEYBOARD PAUSE' if self.keyboard_pause else 'FIST PAUSE - open palm to resume'
            return
        if self.paused:
            if open_hand:
                if self.open_since is None:
                    self.open_since = now
                if now - self.open_since >= RESUME_HOLD:
                    self.paused = False
                    self.cooldown_until = now + COOLDOWN
                    self.cursor = tuple(self.mouse.position())
            else:
                self.open_since = None
            self.label = 'Show open palm to resume' if self.paused else 'READY'
            return

        # LEFT fist has priority over pinches encountered while closing the hand.
        if click_available and left_closed:
            if self.mode or self.dragging:
                ready = self.double_ready and not self.dragging
                self.cancel()  # Cancel pending click; release drag without double-click.
                self.double_ready = ready
            self.armed = False
            self.neutral_since = None
            self.left_open_since = None
            self.scroll_since = self.scroll_y = None
            if self.left_fist_since is None:
                self.left_fist_since = now
            if (self.double_ready and now - self.left_fist_since >= FIST_HOLD
                    and now >= self.cooldown_until):
                self.mouse.click('double')
                self.double_ready = False
                self.cooldown_until = now + COOLDOWN
                self.label = 'DOUBLE CLICK - open LEFT palm before next click'
            else:
                self.label = ('LEFT FIST - hold briefly' if self.double_ready
                              else 'Open LEFT palm to rearm double-click')
            return  # Freeze cursor on target while double-clicking.
        self.left_fist_since = None
        if click_available and left_open and min(ratios.values()) >= PINCH_OFF:
            if self.left_open_since is None:
                self.left_open_since = now
            if now - self.left_open_since >= FIST_REARM:
                self.double_ready = True
        else:
            self.left_open_since = None

        # Once pinching, lock the gesture until its own release threshold.
        if self.mode:
            ratio = ratios[self.mode]
            elapsed = now - self.started
            if ratio >= PINCH_OFF:
                if self.dragging:
                    self.mouse.release()
                elif elapsed >= DEBOUNCE:
                    self.mouse.click(self.mode)
                self.dragging = False
                self.mode = None
                self.armed = False
                self.neutral_since = None
                self.cooldown_until = now + COOLDOWN
                self.cursor = None
                self.label = 'RELEASED'
                return
            if self.mode == 'left' and elapsed >= DRAG_HOLD:
                if not self.dragging:
                    self.mouse.down()
                    self.dragging = True
                    self.previous_target = None
                self.move(target, dt, relative=True)
            self.label = 'DRAGGING' if self.dragging else self.mode.upper() + ' PINCH - release to click'
            return

        neutral = min(ratios.values()) >= PINCH_OFF
        if neutral and click_available:
            if self.neutral_since is None:
                self.neutral_since = now
            if now - self.neutral_since >= DEBOUNCE and now >= self.cooldown_until:
                self.armed = True
        else:
            self.neutral_since = None

        if click_available and self.armed and min(ratios.values()) < PINCH_ON:
            self.mode = min(ratios, key=ratios.get)
            self.started = now
            self.scroll_since = None
            self.scroll_y = None
            self.armed = False
            self.label = self.mode.upper() + ' PINCH'
            return

        scroll_pose = extended[0] and extended[1] and not extended[2] and not extended[3]
        if scroll_pose and neutral:
            if self.scroll_since is None:
                self.scroll_since = now
                self.scroll_y = target[1]
            if now - self.scroll_since >= SCROLL_HOLD:
                delta = self.scroll_y - target[1]
                steps = int(delta / SCROLL_STEP)
                if steps:
                    steps = int(clamp(steps, -5, 5))
                    self.mouse.scroll(steps)
                    self.scroll_y -= steps * SCROLL_STEP
            self.label = 'SCROLL - V sign up/down'
            self.cursor = None
            return
        self.scroll_since = None
        self.scroll_y = None
        if extended[0] and neutral:
            self.move(target, dt)
            self.label = 'MOVE'
        else:
            self.label = 'READY - extend index finger'
            self.cursor = None


class MacMouse:
    def __init__(self, preview=False):
        import pyautogui
        import Quartz
        self.pg = pyautogui
        self.q = Quartz
        self.preview = preview
        self.size = tuple(pyautogui.size())
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.01

    def position(self):
        return self.pg.position()

    def move(self, x, y, dragging=False):
        if self.preview:
            return
        self.pg.failSafeCheck()
        if dragging:
            event = self.q.CGEventCreateMouseEvent(
                None, self.q.kCGEventLeftMouseDragged, (x, y), self.q.kCGMouseButtonLeft)
            self.q.CGEventPost(self.q.kCGHIDEventTap, event)
        else:
            self.pg.moveTo(round(x), round(y))

    def click(self, button):
        if not self.preview:
            if button == 'double':
                self.pg.doubleClick(interval=0.12, button='left')
            else:
                self.pg.click(button=button)

    def down(self):
        if not self.preview:
            self.pg.mouseDown(button='left')

    def release(self):
        if not self.preview:
            # Direct release still works when the cursor is at a failsafe corner.
            event = self.q.CGEventCreateMouseEvent(
                None, self.q.kCGEventLeftMouseUp, tuple(self.position()), self.q.kCGMouseButtonLeft)
            self.q.CGEventPost(self.q.kCGHIDEventTap, event)

    def scroll(self, steps):
        if not self.preview:
            self.pg.scroll(steps)


def select_hands(results, width, height):
    """MediaPipe handedness expects the mirrored image used here.
    Reject uncertain/duplicate labels instead of choosing by list order or x.
    """
    detected = {}
    landmarks_list = results.multi_hand_landmarks or []
    handedness = results.multi_handedness or []
    if len(landmarks_list) != len(handedness):
        return {}, True
    for landmarks, classification in zip(landmarks_list, handedness):
        info = classification.classification[0]
        if info.score < 0.75 or info.label not in ('Right', 'Left'):
            return {}, True
        if info.label in detected:
            return {}, True
        points = [(p.x * width, p.y * height) for p in landmarks.landmark]
        palm = distance(points[5], points[17])
        if palm < 25:
            continue
        detected[info.label] = (landmarks, points, palm)
    return detected, False


def accessibility_trusted():
    services = ctypes.CDLL(
        "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    )
    check = services.AXIsProcessTrusted
    check.argtypes = []
    check.restype = ctypes.c_bool
    return bool(check())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='Detect gestures without mouse actions')
    parser.add_argument('--camera', type=int, default=0)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise SystemExit('This version is for macOS.')
    import cv2
    import mediapipe as mp
    mouse = MacMouse(args.preview)
    if not args.preview and not accessibility_trusted():
        print('Enable Terminal under System Settings > Privacy & Security > Accessibility.')
        print('Quit and reopen Terminal, activate .venv, and run again. Or use --preview.')
        return
    cv2.setNumThreads(1)
    controller = Controller(mouse)
    camera = cv2.VideoCapture(args.camera, cv2.CAP_AVFOUNDATION)
    title = 'HandMouse V2 - Two Hands'
    draw = True
    try:
        if not camera.isOpened():
            print('Camera unavailable. Check Camera permission and close other camera apps.')
            return
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, FPS)
        print('RIGHT hand: move/scroll/pause. LEFT hand: click/double-click/drag.')
        print('Show RIGHT open palm to start. Keep hands separate, facing camera.')
        print('Preview window focused: Q/Esc quit, Space pause, L landmarks.')
        print('Emergency: use trackpad to move pointer to a screen corner, or Ctrl+C in Terminal.')
        with mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=2, model_complexity=0,
            min_detection_confidence=0.65, min_tracking_confidence=0.65
        ) as hands:
            while True:
                start = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    controller.missing()
                    print('Camera frame lost. Stopping.')
                    break
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                results = hands.process(rgb)
                detected, ambiguous = select_hands(results, w, h)
                for side, (landmarks, points, palm) in detected.items():
                    if draw:
                        mp.solutions.drawing_utils.draw_landmarks(
                            frame, landmarks, mp.solutions.hands.HAND_CONNECTIONS)
                        for i, point in enumerate(points):
                            cv2.putText(frame, str(i), (int(point[0]) + 3, int(point[1]) - 3),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                    role = 'RIGHT: MOVE/SCROLL' if side == 'Right' else 'LEFT: CLICK'
                    wrist = points[0]
                    cv2.putText(frame, role, (max(0, int(wrist[0]) - 70),
                                int(clamp(wrist[1] + 20, 80, h - 10))),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.43, (0, 255, 255), 1)
                if ambiguous:
                    controller.missing()
                    controller.label = 'Hands unclear - separate hands, palms toward camera'
                elif 'Right' not in detected:
                    controller.missing()
                    controller.label = 'Show RIGHT hand to move / resume'
                else:
                    landmarks, points, palm = detected['Right']
                    extended = [finger_up(points, tip) for tip in (8, 12, 16, 20)]
                    left = detected.get('Left')
                    if left:
                        _, left_points, left_palm = left
                        pinches = [distance(left_points[4], left_points[tip]) / left_palm
                                   for tip in (8, 12)]
                        left_extended = [finger_up(left_points, tip) for tip in (8, 12, 16, 20)]
                    else:
                        pinches = [1.0, 1.0]
                        left_extended = [False] * 4
                    controller.update(time.monotonic(),
                        (landmarks.landmark[8].x, landmarks.landmark[8].y),
                        pinches[0], pinches[1], extended,
                        click_available=left is not None,
                        left_closed=left is not None and not any(left_extended),
                        left_open=left is not None and all(left_extended))
                margin = CAMERA_MARGIN
                cv2.rectangle(frame, (int(w * margin), int(h * margin)),
                              (int(w * (1 - margin)), int(h * (1 - margin))), (180, 100, 0), 1)
                cv2.rectangle(frame, (0, 0), (w, 65), (25, 25, 25), -1)
                label = ('PREVIEW | ' if args.preview else '') + controller.label
                cv2.putText(frame, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 230, 230), 1)
                cv2.putText(frame, 'Q/Esc Quit | Space Pause | L Landmarks | Fist Pause',
                            (8, 49), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (255, 255, 255), 1)
                cv2.imshow(title, frame)
                wait_ms = max(1, int((1 / FPS - (time.monotonic() - start)) * 1000))
                key = cv2.waitKey(wait_ms) & 0xFF
                if key in (ord('q'), 27):
                    break
                if key == 32:
                    controller.toggle()
                if key == ord('l'):
                    draw = not draw
                if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
    except mouse.pg.FailSafeException:
        print('Corner failsafe triggered. HandMouse stopped.')
    except KeyboardInterrupt:
        print('\nHandMouse stopped.')
    finally:
        try:
            controller.cancel()
        finally:
            camera.release()
            cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
