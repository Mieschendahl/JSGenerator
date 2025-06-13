import re
import shutil
import subprocess
import json
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
from promptgpt import utils

def get_url(package_name: str) -> str:
    """
    Retrieves the GitHub repository URL of a given npm package using the `npm view` command.

    Args:
        package_name (str): The name of the npm package.

    Returns:
        Optional[str]: The repository URL if found, otherwise None.
    """

    # Run the npm view command with JSON output
    result = run_shell(f"npm view {package_name} repository --json", check=True)

    # Parse the JSON result
    repo_data = json.loads(result)

    # Extract the URL from the repository field
    url = None
    if isinstance(repo_data, dict):
        url = repo_data.get("url")
    elif isinstance(repo_data, str):
        url = repo_data

    assert url is not None
    assert "github.com" in url
    
    return "https://github.com" + url.split("github.com", 1)[-1].split(".git")[0]

def clone_repository(github_url: str, clone_path: Path) -> None:
    """
    Clones a GitHub repository to a specified local directory using 'git clone'.

    Args:
        github_url: The URL of the GitHub repository to be cloned (e.g., 'https://github.com/user/repo.git').
        clone_path: The local directory where the repository should be cloned.
    """
    create_dir(clone_path)
    run_shell(f"git clone --depth 1 {github_url} {clone_path}", check=True)
    
def get_file(repository_path: Path, file_path: Path) -> str:
    path = repository_path / file_path
    
    assert path.is_file()
    
    return path.read_text()

def get_readme(repository_path: Path) -> str:
    """Gets the readme file content of a github repository.

    Args:
        repository_path: The path to the repository.

    Returns:
        str: The content of the README file if found, otherwise None.
    """
    readme_names = [
        'README.md', 'README.rst', 'README.txt', 'README',
        'readme.md', 'readme.rst', 'readme.txt', 'readme'
    ]
    for name in readme_names:
        try:
            return get_file(repository_path, Path(name))
        except:
            pass
    assert False

def get_main(repository_path: Path) -> str:
    """Gets the main file content of a github repository.

    Args:
        repository_path: The path to the repository.

    Returns:
        str: The content of the main file if found, otherwise None.
    """
    package = get_file(repository_path, Path("package.json"))
    package_json = json.loads(package)
    main_file = package_json.get('main', 'index.js')
    return get_file(repository_path, Path(main_file))

def print_examples(examples: list[str]) -> None:
    """Prints a list of examples.

    Args:
        examples (List[str]): The list of examples.
    """
    for i, example in enumerate(examples):
        print(f"EXAMPLE {i+1}:")
        print(utils.pad(example, " | "))
        print()

class ShellError(Exception):
    """Custom exception for shell command errors."""
    
    def __init__(self, output: str, message: str) -> None:
        """Initializes the ShellError with output and message.

        Args:
            output (str): The output from the shell command.
            message (str): The error message.
        """
        super().__init__(message)
        self.output = output

def run_shell(command: str, shell: bool = True, check: bool = True, **kwargs) -> str:
    """Runs a shell command and captures its output.

    Args:
        command (str): The command to run.
        shell (bool, optional): Whether to use the shell. Defaults to True.
        check (bool, optional): Whether to check for errors. Defaults to True.

    Returns:
        str: The output of the command.

    Raises:
        ShellError: If the command fails.
    """
    print(f"Running: {command}")
    output = []
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        executable='/bin/bash',
        shell=True,
        text=True,
        **kwargs
    ) as process:
        if process.stdout is not None:
            for line in process.stdout:
                print(line, end="")
                output.append(line)
        output = "".join(output).strip()
        print()
    if check and process.returncode != 0:
        raise ShellError(output, f"Shell command '{command}' exit with code {process.returncode}")
    return output

def create_dir(dir_path: Path, src_path: Optional[Path] = None, remove: bool = True) -> None:
    """Creates a directory, optionally copying from a source path.

    Args:
        dir_path (Path): The path to the directory to create.
        src_path (Optional[Path], optional): The source path to copy from. Defaults to None.
        remove (bool, optional): Whether to remove the existing directory. Defaults to True.
    """
    if remove:
        shutil.rmtree(dir_path, ignore_errors=True)
    if src_path is None:
        dir_path.mkdir(parents=True, exist_ok=True)
    else:
        shutil.copytree(src_path, dir_path, dirs_exist_ok=True)

def parse_examples(response: str) -> list[str]:
    """Parses examples from a response string.

    Args:
        response (str): The response string containing examples.
        split (str): The delimiter to split the examples.

    Returns:
        List[str]: A list of cleaned code examples.
    """
    
    pattern = r"```js?\n(.*?)```"
    code_blocks = re.findall(pattern, response, flags=re.DOTALL)
    return [match.strip() for match in code_blocks]

def filter_examples(examples: list[str], template_path: Path, project_path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Filter valid JavaScript examples.

    Args:
        package_name (str): The name of the npm package.
        examples (list[str]): A list of JavaScript code examples.

    Returns:
        list[str]: A list of valid JavaScript examples that run successfully.
    """
    valid_examples: list[str] = []
    invalid_examples: list[tuple[str, str]] = []
    for example in examples:
        create_dir(project_path, template_path)
        file_path = project_path / "index.js"
        file_path.write_text(example)
        try:
            run_shell(f"node {file_path.name}", cwd=project_path)
            valid_examples.append(example)
        except ShellError as e:
            invalid_examples.append((example, e.output))
    return valid_examples, invalid_examples