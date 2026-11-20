"""KlarBild starten:  python3 main.py [Dateien …]   ·   Selbsttest:  python3 main.py --selftest"""
import sys

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        from klarbild.selftest import run
        sys.exit(run())
    from klarbild.gui.app import main
    sys.exit(main())
