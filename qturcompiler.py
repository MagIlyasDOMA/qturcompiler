import argparse
import subprocess
from os.path import splitext
from importlib.metadata import metadata as get_package_metadata, PackageNotFoundError
from typing import Literal, get_args
from pathlib import Path

QtLibraries = Literal['pyside6', 'pyqt6', 'pyqt5', 'pyside2']
FileType = Literal['ui', 'qrc']
COMPILERS = {
    'ui': {
        'pyside6': 'pyside6-uic',
        'pyqt6': 'pyuic6',
        'pyqt5': 'pyuic5',
        'pyside2': 'pyside2-uic',
    },
    'qrc': {
        'pyside6': 'pyside6-rcc',
        'pyqt6': 'pyrcc6',
        'pyside2': 'pyside2-rcc',
    }
}


class QtNotFound(Exception): pass


class IncorrectFileType(Exception): pass


def is_package_installed(package: str) -> bool:
    try: get_package_metadata(package)
    except PackageNotFoundError: return False
    else: return True


def get_qt_lib():
    for package in get_args(QtLibraries):
        if is_package_installed(package):
            return package
    raise QtNotFound


def get_compiler(filetype: FileType, qtlib: QtLibraries = None):
    if qtlib is None: qtlib = get_qt_lib()
    return COMPILERS[filetype][qtlib]


def qtur_file(value) -> Path:
    value = Path(value)
    if not value.is_file(): raise FileNotFoundError(value)
    if value.suffix not in ('.qrc', '.ui'): raise IncorrectFileType(value)
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Compile Qt UI (.ui) and resource (.qrc) files into Python modules.",
        epilog="If no Qt library is specified, the first installed one from the list "
               "(pyside6, pyqt6, pyqt5, pyside2) is used."
    )
    parser.add_argument('files', nargs='*', type=qtur_file,
                        help='.ui or .qrc files to compile')

    libs_group = parser.add_mutually_exclusive_group()
    libs_group.add_argument('--pyside6', action='store_const', const='pyside6', dest='qtlib',
                            help='Use PySide6')
    libs_group.add_argument('--pyqt6', action='store_const', const='pyqt6', dest='qtlib',
                            help='Use PyQt6')
    libs_group.add_argument('--pyqt5', action='store_const', const='pyqt5', dest='qtlib',
                            help='Use PyQt5')
    libs_group.add_argument('--pyside2', action='store_const', const='pyside2', dest='qtlib',
                            help='Use PySide2')

    try:
        args = parser.parse_args()
        qtlib = args.qtlib or get_qt_lib()
        files = args.files

        for file in files:
            file: Path
            root, ext = splitext(file)
            filetype: FileType = ext[1:].lower()  # type: ignore

            if filetype == 'qrc' and qtlib == 'pyqt6': parser.error('Resources (.qrc) are not supported in PyQt6')

            subprocess.run(
                [get_compiler(filetype, qtlib), str(file), '-o', root + '.py'],
                check=True, text=True
            )

    except Exception as error:
        error_module = error.__class__.__module__
        error_module = '' if error_module == '__main__' else error_module + '.'
        parser.error(f"{error_module}{error.__class__.__name__}: {error}")


if __name__ == '__main__': main()