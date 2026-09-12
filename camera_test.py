import cv2


def main():
    camera = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)

    try:
        if not camera.isOpened():
            print("Camera could not open. Check Camera permission.")
            return

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)

        print("Camera opened. Click the video window and press Q to quit.")

        while True:
            success, frame = camera.read()

            if not success:
                print("Could not read a camera frame.")
                break

            frame = cv2.flip(frame, 1)

            cv2.putText(
                frame,
                "HandMouse Camera Test | Q: Quit",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            cv2.imshow("HandMouse - Camera Test", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

            if cv2.getWindowProperty(
                "HandMouse - Camera Test", cv2.WND_PROP_VISIBLE
            ) < 1:
                break

    except KeyboardInterrupt:
        print("\nCamera test stopped.")
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
