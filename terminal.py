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
    func: Callable[[list[str], Callable[[str], Any], list[str] | None], Any]


commands: dict[str, Command] = {}


def cmd(name: str, description: str = "", usage: str | None = None):
    if usage is None:
        usage = name

    def decorator(func: Callable[[list[str], Callable[[str], Any], list[str] | None], Any]):
        commands[name] = Command(name, description, usage, func)
        return func

    return decorator


@cmd("exit", "Exit the terminal")
def exit_terminal(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    global running
    running = False


@cmd("cd", "Change the current directory", "cd <folder_name>")
def change_directory(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    global cwd
    if piped:
        folder_name = piped[0]
    else:
        if len(args) < 1:
            out("Missing folder name.")
            return
        folder_name = args[0]
    next_folder = cwd.retrieve_path(folder_name)
    if isinstance(next_folder, Folder):
        cwd = next_folder
    else:
        out(f"Folder {folder_name} not found.")


@cmd("ls", "List the contents of the current directory")
def list_contents(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    for content in cwd.contents:
        out(content.name)


@cmd("rd", "Print out the contents of a file", "rd <file_name>")
def read_file(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if piped:
        file = piped[0]
    else:
        if len(args) < 1:
            out("Missing file name.")
            return
        file = cwd.retrieve_path(args[0])
    if isinstance(file, File):
        file.for_line(out)
    else:
        out(f"File {file} not found.")


@cmd("rn", "Rename a file or folder", "rn <old_name> <new_name>")
def rename(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if len(args) < 1:
        out("Missing original name.")
        return
    if len(args) < 2:
        out("Missing new name.")
        return

    old_name = args[0]
    new_name = args[1]

    content = cwd.get_content(old_name)
    if content is None:
        out(f"File or folder {old_name} not found.")
        return

    conflict = cwd.get_content(new_name)
    if conflict is not None:
        out(f"A file or folder with name {new_name} already exists.")
        return

    content.update_name(new_name)


@cmd("ex", "Execute a file", "ex <file_name>")
def execute_file(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if piped:
        file = piped[0]
    else:
        if len(args) < 1:
            out("Missing file name.")
            return

        file = cwd.retrieve_path(args[0])
    if not isinstance(file, File):
        out(f"File {file} not found.")
        return

    if file.extension != "ex":
        out(f"File {file} is not a .ex file.")
        return

    file.for_line(lambda line: run_command_piping(line, out))

@cmd("echo", "Print a message to the output buffer", "echo <message>")
def echo(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if piped:
        message = piped[0]
    else:
        if len(args) < 1:
            out("Missing message.")
            return
        message = " ".join(args)
    out(message)


@cmd("pwd", "Print the current working directory")
def print_working_directory(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    out(cwd.path)


@cmd("help", "Show this help message")
def help(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    out("Available commands:")
    for command in commands.values():
        out(f"{command.name}: {command.description} ({command.usage})")
    out("")


# commands: dict[str, Callable[[list[str]], Any]] = {
#     "cd": change_directory,
#     "ls": lambda args: [print(content.name) for content in cwd.contents],
#     "rd": read_file,
#     "pwd": lambda args: print(cwd.path),
# }


def run_command_piping(command: str, out: Callable[[str], Any] = print):
    cmd_list = command.split(";")
    for cmd in cmd_list:
        cmds = cmd.split("|")
        output_buffer: list[str] = []
        for i, c in enumerate(cmds):
            if i == len(cmds) - 1:
                run_command(c.strip(), out, output_buffer)
            else:
                output_buffer.clear()
                run_command(c.strip(), output_buffer.append, output_buffer)

def run_command(command: str, out: Callable[[str], Any] = print, piped: list[str] | None = None):
    cmd_prefix = command.split(" ")[0]

    if cmd_prefix in commands:
        commands[cmd_prefix].func(get_args(command), out, piped)
    else:
        out(f"Unknown command: {cmd_prefix}")


def run_terminal():
    global running
    running = True
    while running:
        command = input(f"{cwd.path}> ")
        run_command_piping(command)
        # cmd_list = command.split(";")
        # for cmd in cmd_list:
        #     cmds = cmd.split("|")
        #     output_buffer: list[str] = []
        #     for i, c in enumerate(cmds):
        #         c += " " + " ".join(output_buffer) if output_buffer else ""
        #         if i == len(cmds) - 1:
        #             run_command(c.strip(), print)
        #         else:
        #             output_buffer.clear()
        #             run_command(c.strip(), output_buffer.append)

        # run_command(command)


if __name__ == "__main__":
    run_terminal()
