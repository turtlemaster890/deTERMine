from __future__ import annotations
from typing import Any, Callable


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

    def update_name(self, new_name: str):
        self.name = new_name
        self.update_path(self.parent.path if self.parent else "")

    def matches(self, name: str) -> bool:
        return self.name == name

    def print(self):
        for line in self.content:
            print(line)

    def for_line(self, method: Callable[[str], Any]):
        for line in self.content:
            method(line)

    @property
    def extension(self) -> str:
        if "." in self.name:
            return self.name.split(".")[-1]
        return ""


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

    def update_name(self, new_name: str):
        self.name = new_name
        self.update_path(self.parent.path if self.parent else "")
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

    def retrieve_path(self, path: str, root: Folder, prefer: type[Folder | File] | None = None) -> File | Folder | None:
        parts = path.split("/")
        return self.retrieve_path_by_parts(parts, root, prefer=prefer)

    def retrieve_path_by_parts(self, parts: list[str], root: Folder, prefer: type[Folder | File] | None = None) -> File | Folder | None:
        current_folder: Folder = root

        if parts[0] == "." or parts[0] == "..":
            current_folder = self

        elif parts[0] == "root":
            parts = parts[1:]

        for part in parts:
            # if self.matches(part):
            #     continue

            if part == ".":
                continue

            if part == "..":
                if current_folder.parent is not None:
                    current_folder = current_folder.parent
                else:
                    return None
                continue

            if prefer is Folder:
                next_content = current_folder.get_folder(part)
                if next_content is None:
                    next_content = current_folder.get_file(part)
            elif prefer is File:
                next_content = current_folder.get_file(part)
                if next_content is None:
                    next_content = current_folder.get_folder(part)
            else:
                next_content = current_folder.get_content(part)
            if next_content is None:
                return None

            if isinstance(next_content, Folder):
                current_folder = next_content
            else:
                return next_content

        return current_folder

    def find(self, name: str, exact: bool) -> list[File | Folder]:
        results: list[File | Folder] = []
        for content in self.contents:
            if exact:
                if content.matches(name):
                    results.append(content)
            else:
                if name in content.name:
                    results.append(content)

            if isinstance(content, Folder):
                results.extend(content.find(name, exact))
        return results
