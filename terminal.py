from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, overload

from Internals import AccessBuilder, File, Folder

running: bool = True

prev_superuser: bool = False
superuser: bool = False


def access(condition: Callable[[], bool]):
    def decorator(func: Callable[..., Any]):
        def wrapper(*args, **kwargs):
            if condition():
                return func(*args, **kwargs)
            else:
                raise PermissionError("Access denied.")

        return wrapper

    return decorator


def combine_access(condition: Callable[[], bool]) -> Callable[[], bool]:
    def combined_condition() -> bool:
        return superuser or condition()

    return combined_condition


def command_is(command: str, prefix: str) -> bool:
    if command.startswith(prefix + " "):
        return True
    return command == prefix


def get_args(command: str) -> list[str]:
    return command.split(" ")[1:]


root: Folder = Folder(
    "",
    [
        Folder(
            "folder1",
            [
                File("file1.txt", ["Hello, World!"]),
                Folder("subfolder1", [File("file2.txt", ["This is a test file."])]),
            ],
        ),
        Folder(
            "folder2",
            [
                File(
                    "file3.txt",
                    ["Another file."],
                    access=AccessBuilder.default()
                    .read(combine_access(lambda: input("Enter password: ") == "12345"))
                    .write(lambda: superuser),
                )
            ],
        ),
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

T = TypeVar("T", File, Folder)


@overload
def get(name: str, expected_type: type[T]) -> T | None: ...


@overload
def get(name: str, expected_type: type[File | Folder]) -> File | Folder | None: ...


def get(
    name: str, expected_type: type[T] | type[File | Folder]
) -> T | File | Folder | None:
    content = cwd.retrieve_path(
        name,
        root,
        prefer=expected_type if expected_type is not (File | Folder) else None,
    )
    if isinstance(content, expected_type):
        return content
    return None
    # content = cwd.retrieve_path(
    #     name,
    #     cwd,
    #     prefer=expected_type if expected_type is not (File | Folder) else None,
    # )
    # if isinstance(content, expected_type):
    #     return content
    # content = cwd.retrieve_path(
    #     name,
    #     root,
    #     prefer=expected_type if expected_type is not (File | Folder) else None,
    # )
    # if isinstance(content, expected_type):
    #     return content
    # return None


class StopExecution(Exception):
    pass


def cmd(name: str, description: str = "", usage: str | None = None):
    if usage is None:
        usage = name

    def decorator(
        func: Callable[[list[str], Callable[[str], Any], list[str] | None], Any],
    ):
        commands[name] = Command(name, description, usage, func)
        return func

    return decorator


@cmd("exit", "Exit the terminal")
def exit_terminal(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    global running
    running = False


@cmd("cd", "Change the current directory", "cd <folder_name>")
def change_directory(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    global cwd
    if piped:
        folder_name = piped[0]
    else:
        if len(args) < 1:
            out("Missing folder name.")
            raise StopExecution
        folder_name = args[0]
    next_folder = get(folder_name, Folder)
    if next_folder is not None:
        cwd = next_folder
    else:
        out(f"Folder {folder_name} not found.")
        raise StopExecution


@cmd("ls", "List the contents of the current directory")
def list_contents(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    for content in cwd.contents:
        out(content.name)


@cmd("rd", "Print out the contents of a file", "rd <file_name>")
def read_file(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    if piped:
        file_name = piped[0]
    else:
        if len(args) < 1:
            out("Missing file name.")
            raise StopExecution
        file_name = args[0]
    file = get(file_name, File)
    if file is not None:
        file.for_line(out)
    else:
        out(f"File {file_name} not found.")
        raise StopExecution


@cmd("rn", "Rename a file or folder", "rn <old_name> <new_name>")
def rename(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if len(args) < 1:
        out("Missing original name.")
        raise StopExecution
    if len(args) < 2:
        out("Missing new name.")
        raise StopExecution

    old_name = args[0]
    new_name = args[1]

    content = get(old_name, File | Folder)
    if content is None:
        out(f"File or folder {old_name} not found.")
        raise StopExecution

    conflict = get(content.path.removesuffix(content.name) + new_name, File | Folder)
    if conflict is not None:
        out(f"A file or folder with name {new_name} already exists.")
        raise StopExecution

    content.update_name(new_name)


@cmd("ex", "Execute a file", "ex <file_name>")
def execute_file(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    if piped:
        file_name = piped[0]
    else:
        if len(args) < 1:
            out("Missing file name.")
            raise StopExecution
        file_name = args[0]

    file = get(file_name, File)
    if file is None:
        out(f"File {file_name} not found.")
        raise StopExecution

    # if file.extension != "ex":
    #     out(f"File {file_name} is not a .ex file.")
    #     return

    file.for_line(lambda line: run_commands(parse_commands(line)))


@cmd("echo", "Print a message to the output buffer", "echo <message>")
def echo(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if piped:
        message = piped[0]
    else:
        if len(args) < 1:
            out("Missing message.")
            raise StopExecution
        message = " ".join(args)
    out(message)


@cmd("find", "Find files or folders by name", "find <name> [--exact | -e]")
def find(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if piped:
        name = piped[0]
    else:
        if len(args) < 1:
            out("Missing name.")
            raise StopExecution

        name = args[0]

    exact = (
        "--exact" in args
        or ("--exact" in piped if piped else False)
        or "-e" in args
        or ("-e" in piped if piped else False)
    )

    results = cwd.find(name, exact)
    if not results:
        out(f"No files or folders found with name {name}.")
        raise StopExecution

    for result in results:
        out(result.path)


@cmd("pwd", "Print the current working directory")
def print_working_directory(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    out(cwd.path)


@cmd("path", "Print the full path of a file or folder", "path <name>")
def print_path(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    if piped:
        name = piped[0]
    else:
        if len(args) < 1:
            out("Missing name.")
            raise StopExecution
        name = args[0]

    content = get(name, File | Folder)
    if content is None:
        out(f"File or folder {name} not found.")
    else:
        out(content.path)


@cmd("filter", "Filter the output of a command by a keyword", "filter <keyword>")
def filter_output(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    if piped is None:
        out("No input to filter.")
        raise StopExecution

    if len(args) < 1:
        out("Missing keyword.")
        raise StopExecution

    keyword = args[0]
    for line in piped:
        if keyword in line:
            out(line)


@cmd("mk", "Create a new file", "mk <file_name>")
def create_file(
    args: list[str],
    out: Callable[[str], Any],
    piped: list[str] | None = None,
):
    if len(args) < 1:
        out("Missing file name.")
        raise StopExecution

    file_name = args[0]

    conflict = get(file_name, File)
    if conflict is not None:
        out(f"A file named {file_name} already exists.")
        raise StopExecution

    path = "/".join(file_name.split("/")[:-1])
    parent = get(path, Folder) if path else cwd
    if parent is None:
        out(f"Parent folder {path} not found.")
        raise StopExecution

    new_file = File(file_name.split("/")[-1], [])
    parent.add_content(new_file)


@cmd("mkdir", "Create a new folder", "mkdir <folder_name>")
def create_folder(
    args: list[str],
    out: Callable[[str], Any],
    piped: list[str] | None = None,
):
    if len(args) < 1:
        out("Missing folder name.")
        raise StopExecution

    folder_name = args[0]

    conflict = get(folder_name, Folder)
    if conflict is not None:
        out(f"A folder named {folder_name} already exists.")
        raise StopExecution

    path = "/".join(folder_name.split("/")[:-1])
    parent = get(path, Folder) if path else cwd
    if parent is None:
        out(f"Parent folder {path} not found.")
        raise StopExecution

    new_folder = Folder(folder_name.split("/")[-1], [])
    parent.add_content(new_folder)


@cmd("su", "Toggle superuser mode")
@access(lambda: input("Enter superuser password: ") == "root")
def toggle_superuser(
    args: list[str], out: Callable[[str], Any], piped: list[str] | None = None
):
    global superuser
    superuser = not superuser
    out(f"Superuser mode {'enabled' if superuser else 'disabled'}.")


@cmd("sudo", "Run a command with superuser privileges", "sudo <command>")
@access(lambda: input("Enter superuser password: ") == "root")
def sudo(args: list[str], out: Callable[[str], Any], piped: list[str] | None = None):
    if len(args) < 1:
        out("Missing command.")
        raise StopExecution
    global superuser
    global prev_superuser
    prev_superuser = superuser
    superuser = True
    _run_command(args[0], args[1:], out, piped)


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


def split_pipes_and_strings(command: str) -> list[str]:
    out: list[str] = []
    in_string = False
    current_output = ""
    for char in command:
        if char == '"':
            in_string = not in_string
            continue
        elif char == "|" and not in_string:
            out.append(current_output)
            current_output = ""
            continue
        current_output += char
    out.append(current_output)
    return out


@dataclass
class ParsedCommand:
    command: str
    args: list[str]
    output_file: str | None = None
    append_output_file: bool = False
    is_piped: bool = False


def parse_commands(commands: str) -> list[ParsedCommand]:
    parsed_commands: list[ParsedCommand] = []
    current_command = ""
    in_string = False
    escape_next = False
    current_args: list[str] = []
    in_command = True
    current_arg = ""
    output_file: str | None = None
    in_output_file = False
    append_output_file = False
    for i, char in enumerate(commands):
        if escape_next:
            if in_output_file:
                output_file = (output_file or "") + char
            elif in_command:
                current_command += char
            else:
                current_arg += char
            escape_next = False
            continue
        if char == '"':
            in_string = not in_string
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == " " and not in_string:
            if in_command and current_command:
                in_command = False
                continue
            elif not in_output_file:
                if current_arg:
                    current_args.append(current_arg)
                    current_arg = ""
                continue
            else:
                if output_file is not None:
                    in_output_file = False
                continue
        if char == ">" and not in_string:
            if i > 0 and commands[i - 1] == ">":
                append_output_file = True
                continue
            else:
                if current_arg:
                    current_args.append(current_arg)
                    current_arg = ""
                in_output_file = True
                output_file = None
                continue

        if char == "|" and not in_string:
            if output_file is not None:
                print(f"Error: Cannot pipe after redirecting output to a file.")
                return []
            if current_arg:
                current_args.append(current_arg)
                current_arg = ""
            parsed_commands.append(
                ParsedCommand(
                    current_command, current_args, output_file, append_output_file, True
                )
            )
            current_command = ""
            output_file = None
            current_args = []
            in_command = True
            in_output_file = False
            append_output_file = False
            continue

        if char == ";" and not in_string:
            if current_arg:
                current_args.append(current_arg)
                current_arg = ""
            parsed_commands.append(
                ParsedCommand(
                    current_command,
                    current_args,
                    output_file,
                    append_output_file,
                    False,
                )
            )
            current_command = ""
            output_file = None
            current_args = []
            in_command = True
            in_output_file = False
            append_output_file = False
            continue

        if in_output_file:
            output_file = (output_file or "") + char
        elif in_command:
            current_command += char
        else:
            current_arg += char

    if current_arg:
        current_args.append(current_arg)
    if current_command:
        parsed_commands.append(
            ParsedCommand(
                current_command, current_args, output_file, append_output_file, False
            )
        )
    return parsed_commands


def run_command_piping(command: str, out: Callable[[str], Any] = print):
    cmd_list = command.split(";")
    for cmd in cmd_list:
        cmds = split_pipes_and_strings(cmd)
        output_buffer: list[str] = []
        for i, c in enumerate(cmds):
            if i == len(cmds) - 1:
                subcmds = c.split(">>")
                if len(subcmds) > 1:
                    file = get(subcmds[1].strip(), File)
                    if file:
                        run_command(
                            subcmds[0].strip(), file.content.append, output_buffer
                        )
                    else:
                        out(f"File {subcmds[1].strip()} not found.")
                else:
                    subcmds = c.split(">")
                    if len(subcmds) > 1:
                        file = get(subcmds[1].strip(), File)
                        if file:
                            file.content.clear()
                            run_command(
                                subcmds[0].strip(), file.content.append, output_buffer
                            )
                        else:
                            out(f"File {subcmds[1].strip()} not found.")
                    else:
                        run_command(c.strip(), out, output_buffer)

            else:
                output_buffer.clear()
                run_command(c.strip(), output_buffer.append, output_buffer)


def run_command(
    command: str, out: Callable[[str], Any] = print, piped: list[str] | None = None
):
    cmd_prefix = command.split(" ")[0]

    if cmd_prefix in commands:
        commands[cmd_prefix].func(get_args(command), out, piped)
    else:
        out(f"Unknown command: {cmd_prefix}")


def _run_command(
    command: str,
    args: list[str],
    out: Callable[[str], Any],
    piped: list[str] | None = None,
):
    cmd_prefix = command.split(" ")[0]

    if cmd_prefix in commands:
        commands[cmd_prefix].func(args, out, piped)
    else:
        out(f"Unknown command: {cmd_prefix}")


def run_commands(parsed_commands: list[ParsedCommand]):
    output_buffer: list[str] = []
    input_buffer: list[str] = []
    global superuser
    try:
        for cmd in parsed_commands:
            if cmd.is_piped:
                output_buffer.clear()
                _run_command(cmd.command, cmd.args, output_buffer.append, input_buffer)
                input_buffer = output_buffer.copy()
            else:
                if cmd.output_file:
                    file = get(cmd.output_file, File)
                    if file:
                        new_lines: list[str] = []
                        _run_command(
                            cmd.command, cmd.args, new_lines.append, input_buffer
                        )

                        if cmd.append_output_file:
                            file.content = [*file.content, *new_lines]
                        else:
                            file.content = new_lines
                    else:
                        print(f"File {cmd.output_file} not found.")
                        raise StopExecution
                else:
                    _run_command(
                        cmd.command,
                        cmd.args,
                        print,
                        input_buffer if input_buffer else None,
                    )
                input_buffer = []
    except StopExecution:
        for line in output_buffer:
            print(line)
    except PermissionError as e:
        print(e)
    finally:
        superuser = prev_superuser


def run_terminal():
    global running
    running = True
    while running:
        command = input(f"{cwd.path[:-1] if len(cwd.path) > 1 else cwd.path}> ")
        # run_command_piping(command)
        commands = parse_commands(command)
        run_commands(commands)
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
    # print(
    #     parse_commands(
    #         'echo "Hello, World!" ; echo "This is a test." > output.txt ; echo "Done."'
    #     )
    # )
