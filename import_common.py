#!/usr/bin/env python3

import os
import re
from shutil import copytree, ignore_patterns
from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path

parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
parser.add_argument(
    "--function-path",
    type=Path,
    metavar="function_path",
    default=Path("."),
    help="the path of the function to import into."
)
parser.add_argument(
    "--common-path",
    type=Path,
    metavar="common_path",
    default=Path("../common"),
    help="the path to the directory containing the common files."
)
parser.add_argument(
    "--common-package",
    type=str,
    metavar="common_package",
    default="functions.common",
    help="the base package of the 'common function'.\n"
         "this part will be replaced with the function_package."
)
parser.add_argument(
    "--function-package",
    type=str,
    metavar="function_package",
    required=False,
    help="the base package of the function.\n"
         "this part will replace the common_package."
)
parser.add_argument(
    "--remote-uri",
    type=str,
    metavar="remote_uri",
    required=False,
    help="this is the git uri where the common files will be gotten from."
)
parser.add_argument(
    "--remote-clone-path",
    type=Path,
    metavar="remote_clone_path",
    default=Path("../remotes"),
    help="this is the base path where the remote will, temporarily, be cloned to."
)
parser.add_argument(
    "--remote-branch",
    type=str,
    metavar="remote_branch",
    default="master",
    help="the remote's branch to clone"
)


arguments, unknown_arguments = parser.parse_known_args()

IMPORT_REGEX = re.compile(r"^(?:from|import)\s([^\s]+)(?:\simport\s.+)?$")
GIT_CLONE_HTTPS_REGEX = re.compile(r"^https://([^/]+)/([^/]+)/([^/]+).git$")


def clone_remote(remote_uri: str, branch: str, remote_path: Path) -> Path:
    """
    Clones the remote to a path relative to the remote_path.

    :param remote_uri: The URI of the remote.
    :type remote_uri: str
    :param branch: The branch of the remote.
    :type branch: str
    :param remote_path: The root path where remotes will be cloned to.
    :type remote_path: Path
    :return: The folder of the cloned remote.
    :rtype: Path
    """
    result = GIT_CLONE_HTTPS_REGEX.search(remote_uri)
    if result:
        repo_owner = result.group(2)
        repo_name = result.group(3)

        remote_path = remote_path.joinpath(repo_owner).joinpath(repo_name).joinpath(branch)

        if remote_path.exists():
            print("Remote already cloned, moving on.")
        else:
            return_value = os.system(f"git clone --branch {branch} {remote_uri} {str(remote_path)}")  # nosec
            if return_value:
                print(f"Could not clone '{remote_uri}''s branch '{branch}'.")
                remote_path = None
    else:
        print(f"Invalid URI: {remote_uri}")
        remote_path = None
    return remote_path


def process_lines(lines: list[str], common_package, function_package) -> list[str]:
    """
    Processed the lines of the file by looking for imports of the common package.

    :param lines: The lines of the Python file.
    :type lines: list[str]
    :param common_package: The package to be replaced.
    :type common_package: str
    :param function_package: The package to replace common_package with.
    :type function_package: str
    :return: The processed lines.
    :rtype: list[str]
    """
    for i, line in enumerate(lines):
        result = IMPORT_REGEX.search(line)
        if result:
            package = result.group(1)
            if package.startswith(common_package):
                lines[i] = line.replace(common_package, function_package)

    return [line for line in lines if line]


def main() -> int:
    """
    This script will allow for easy import and reuse of code for the cloud.
    It does this by copying, and processing all required files to the folder
    that will be deployed to the cloud.

    :return: Exit code.
    :rtype: int
    """
    function_path = arguments.function_path
    common_path = arguments.common_path

    if arguments.remote_uri:
        common_path = clone_remote(
            arguments.remote_uri,
            arguments.remote_branch,
            arguments.remote_clone_path
        ).joinpath(common_path)

    if not function_path or not os.path.exists(function_path) or not os.path.isdir(function_path):
        print(f"'{arguments.function_path}' is not a valid directory.")
        return 1

    if not common_path or not os.path.exists(common_path) or not os.path.isdir(common_path):
        print(f"'{common_path}' is not a valid directory.")
        return 1

    if arguments.function_package:
        function_package = arguments.function_package
    elif arguments.common_path.resolve().name in arguments.common_package:
        function_package = arguments.common_package.replace(
            arguments.common_path.resolve().name,
            arguments.function_path.resolve().name
        )
    else:
        print(
            "Could not resolve function_package from common_package.\n"
            "Please check common_package, or consider specifying --function-package"
        )
        return 1

    for file in function_path.glob("**/*.py"):
        with open(file, "r") as open_file:
            lines = open_file.readlines()

        lines = process_lines(lines, arguments.common_package, function_package)

        with open(file, "w") as open_file:
            open_file.writelines(lines)

    copytree(str(common_path), str(function_path), dirs_exist_ok=True, ignore=ignore_patterns(".*"))

    return 0


if __name__ == "__main__":
    exit(main())
