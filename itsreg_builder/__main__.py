import sys

from itsreg_builder.app import App


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else "script.json"
    app = App(file_path)
    app.run()


if __name__ == "__main__":
    main()
