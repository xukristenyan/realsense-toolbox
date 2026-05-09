"""
Quick interactive test for KeyListener.
Press s, e, or esc. ESC exits.
"""
import time
from realsense_toolbox.utils import KeyListener


def main():
    print("Press 's', 'e', or ESC (esc to exit). Other keys also report.")
    with KeyListener() as keys:
        while True:
            for k in ("s", "e", "esc", "a", "b", "c"):
                if keys.consume_pressed(k):
                    print(f"  pressed: {k!r}")
                    if k == "esc":
                        return
            time.sleep(0.05)


if __name__ == "__main__":
    main()
