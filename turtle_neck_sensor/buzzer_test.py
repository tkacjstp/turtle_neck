"""Test a passive buzzer on Raspberry Pi BCM GPIO 2."""
from time import sleep

from gpiozero import TonalBuzzer


BUZZER_PIN = 2
TONE_HZ = 880
ON_SECONDS = 0.6
OFF_SECONDS = 0.4


def main():
    print(f"Testing buzzer on BCM GPIO {BUZZER_PIN} at {TONE_HZ} Hz. Press Ctrl+C to stop.")
    with TonalBuzzer(BUZZER_PIN) as buzzer:
        try:
            while True:
                buzzer.play(TONE_HZ)
                sleep(ON_SECONDS)
                buzzer.stop()
                sleep(OFF_SECONDS)
        except KeyboardInterrupt:
            pass
        finally:
            buzzer.stop()


if __name__ == "__main__":
    main()
