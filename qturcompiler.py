import argparse
import os
import subprocess
from os.path import splitext
from importlib.metadata import metadata as get_package_metadata, PackageNotFoundError
from typing import Literal, get_args, List
from pathlib import Path

__version__ = '0.3.0'

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


def get_all_files(recursive: bool, exclude_qrc: bool) -> List[Path]:
    cwd = Path.cwd()
    func = cwd.rglob if recursive else cwd.glob
    ui_files = list(func('*.ui'))
    return ui_files + list(func('*.qrc')) if not exclude_qrc else ui_files


def set_working_directory(cwd: Path):
    if cwd == Path.cwd(): return
    if cwd.is_dir(): os.chdir(cwd)
    else: raise FileNotFoundError(cwd)


def main():
    old_dir = os.getcwd()
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

    parser.add_argument('--recursive', '--recurse', '-r', action='store_true', dest='recursive', help='Compile all Qt files recursively')
    parser.add_argument('--version', '-v', action='version', version=__version__)
    parser.add_argument('--cwd', '-d', default=Path.cwd(), type=Path, help='path to working directory')

    try:
        args = parser.parse_args()
        set_working_directory(args.cwd)

        qtlib = args.qtlib or get_qt_lib()
        files = args.files or get_all_files(args.recursive, qtlib == 'pyqt6')

        for file in files:
            file: Path
            root, ext = splitext(file)
            filetype: FileType = ext[1:].lower()  # type: ignore

            if filetype == 'qrc' and qtlib == 'pyqt6': parser.error('Resources (.qrc) are not supported in PyQt6')
            suffix = '_rc' if filetype == 'qrc' else ''

            subprocess.run(
                [get_compiler(filetype, qtlib), str(file), '-o', root + suffix + '.py'],
                check=True, text=True
            )
    except Exception as error:
        error_module = error.__class__.__module__
        error_module = '' if error_module == '__main__' else error_module + '.'
        parser.error(f"{error_module}{error.__class__.__name__}: {error}")
    finally: os.chdir(old_dir)


if __name__ == '__main__': main()
