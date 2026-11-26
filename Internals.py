from __future__ import annotations

from collections.abc import Callable
from typing import Any


class File:
    def __init__(
        self,
        name: str,
        content: list[str],
        path: str = "",
        parent: Folder | None = None,
    ):
        self.name = name
        self.content = content

        self.path = path + "/" + name if path else name

        self.parent: Folder | None = parent

    def update_parent(self, parent: Folder):
        self.parent = parent

    def update_path(self, path: str):
        self.path = path + "/" + self.name if path else self.name

    def matches(self, name: str) -> bool:
        return self.name == name

    def print(self):
        for line in self.content:
            print(line)


class Folder:
    def __init__(
        self,
        name: str,
        contents: list[File | Folder],
        path: str = "",
        parent: Folder | None = None,
    ):
        self.name = name
        self.contents = contents

        self.path = path + "/" + name if path else name

        self.parent: Folder | None = parent

        for content in self.contents:
            content.update_path(self.path)
            content.update_parent(self)

    def update_parent(self, parent: Folder):
        self.parent = parent
        for content in self.contents:
            content.update_parent(self)

    def update_path(self, path: str):
        self.path = path + "/" + self.name if path else self.name
        for content in self.contents:
            content.update_path(self.path)

    def matches(self, name: str) -> bool:
        return self.name == name

    def get_file(self, name: str) -> File | None:
        for content in self.contents:
            if isinstance(content, File) and content.matches(name):
                return content
        return None

    def get_folder(self, name: str) -> Folder | None:
        for content in self.contents:
            if isinstance(content, Folder) and content.matches(name):
                return content
        return None

    def get_content(self, name: str) -> File | Folder | None:
        for content in self.contents:
            if content.matches(name):
                return content
        return None

    def retrieve_path(self, path: str) -> File | Folder | None:
        parts = path.split("/")
        return self.retrieve_path_by_parts(parts)

    def retrieve_path_by_parts(self, parts: list[str]) -> File | Folder | None:
        current_folder: Folder = self

        for part in parts:
            if self.matches(part):
                continue

            if part == ".":
                continue

            if part == "..":
                if current_folder.parent is not None:
                    current_folder = current_folder.parent
                else:
                    return None
                continue

            next_content = current_folder.get_content(part)
            if next_content is None:
                return None

            if isinstance(next_content, Folder):
                current_folder = next_content
            else:
                return next_content

        return current_folder


def command_is(command: str, prefix: str) -> bool:
    if command.startswith(prefix + " "):
        return True
    return command == prefix


def get_args(command: str) -> list[str]:
    return command.split(" ")[1:]


root: Folder = Folder(
    "root",
    [
        Folder(
            "folder1",
            [
                File("file1.txt", ["Hello, World!"]),
                Folder("subfolder1", [File("file2.txt", ["This is a test file."])]),
            ],
        ),
        Folder("folder2", [File("file3.txt", ["Another file."])]),
    ],
)

cwd: Folder = root


def change_directory(args: list[str]):
    global cwd
    if len(args) < 1:
        print("Missing folder name.")
        return
    folder_name = args[0]
    next_folder = cwd.retrieve_path(folder_name)
    if isinstance(next_folder, Folder):
        cwd = next_folder
    else:
        print(f"Folder {folder_name} not found.")


def read_file(args: list[str]):
    if len(args) < 1:
        print("Missing file name.")
        return
    file = cwd.retrieve_path(args[0])
    if isinstance(file, File):
        file.print()
    else:
        print(f"File {args[0]} not found.")


commands: dict[str, Callable[[list[str]], Any]] = {
    "cd": change_directory,
    "ls": lambda args: [print(content.name) for content in cwd.contents],
    "rd": read_file,
    "pwd": lambda args: print(cwd.path),
}

while True:
    command = input(f"{cwd.path}> ")
    if command == "exit":
        break

    cmd_prefix = command.split(" ")[0]

    if cmd_prefix in commands:
        commands[cmd_prefix](get_args(command))
    else:
        print(f"Unknown command: {cmd_prefix}")
