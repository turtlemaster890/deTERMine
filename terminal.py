from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from Internals import File, Folder

running: bool = True


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


@dataclass
class Command:
    name: str
    description: str
    usage: str
    func: Callable[[list[str]], Any]


commands: dict[str, Command] = {}


def cmd(name: str, description: str = "", usage: str | None = None):
    if usage is None:
        usage = name

    def decorator(func: Callable[[list[str]], Any]):
        commands[name] = Command(name, description, usage, func)
        return func

    return decorator


@cmd("exit", "Exit the terminal")
def exit_terminal(args: list[str]):
    global running
    running = False


@cmd("cd", "Change the current directory", "cd <folder_name>")
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


@cmd("ls", "List the contents of the current directory")
def list_contents(args: list[str]):
    for content in cwd.contents:
        print(content.name)


@cmd("rd", "Print out the contents of a file", "rd <file_name>")
def read_file(args: list[str]):
    if len(args) < 1:
        print("Missing file name.")
        return
    file = cwd.retrieve_path(args[0])
    if isinstance(file, File):
        file.print()
    else:
        print(f"File {args[0]} not found.")


@cmd("rn", "Rename a file or folder", "rn <old_name> <new_name>")
def rename(args: list[str]):
    if len(args) < 1:
        print("Missing original name.")
        return
    if len(args) < 2:
        print("Missing new name.")
        return

    old_name = args[0]
    new_name = args[1]

    content = cwd.get_content(old_name)
    if content is None:
        print(f"File or folder {old_name} not found.")
        return

    conflict = cwd.get_content(new_name)
    if conflict is not None:
        print(f"A file or folder with name {new_name} already exists.")
        return

    content.update_name(new_name)


@cmd("pwd", "Print the current working directory")
def print_working_directory(args: list[str]):
    print(cwd.path)


@cmd("help", "Show this help message")
def help(args: list[str]):
    print("Available commands:")
    for command in commands.values():
        print(f"{command.name}: {command.description} ({command.usage})")
    print()


# commands: dict[str, Callable[[list[str]], Any]] = {
#     "cd": change_directory,
#     "ls": lambda args: [print(content.name) for content in cwd.contents],
#     "rd": read_file,
#     "pwd": lambda args: print(cwd.path),
# }


def run_terminal():
    global running
    running = True
    while running:
        command = input(f"{cwd.path}> ")
        cmd_prefix = command.split(" ")[0]

        if cmd_prefix in commands:
            commands[cmd_prefix].func(get_args(command))
        else:
            print(f"Unknown command: {cmd_prefix}")


if __name__ == "__main__":
    run_terminal()
