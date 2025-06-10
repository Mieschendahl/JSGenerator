import re
import shutil
import subprocess
import requests
from typing import Optional
from urllib.parse import urlparse
from pathlib import Path
from promptgpt import utils, prebuilt

def get_url(package_name: str) -> Optional[str]:
    """Fetches the GitHub repository URL for a given npm package.

    Args:
        package_name (str): The name of the npm package.

    Returns:
        Optional[str]: The GitHub repository URL if found, otherwise None.
    """
    registry_url = f"https://registry.npmjs.org/{package_name}"

    try:
        response = requests.get(registry_url, timeout=10)
        response.raise_for_status()
        package_data = response.json()

        # 'repository' can be a dict or a string
        repository_info = package_data.get("repository")

        if isinstance(repository_info, dict):
            url = repository_info.get("url")
        elif isinstance(repository_info, str):
            url = repository_info
        else:
            return None

        if url and "github.com" in url:
            # Normalize the URL by stripping prefixes like git+
            url = url.replace("git+", "").replace(".git", "").strip()
            return url

    except (requests.RequestException, ValueError, KeyError):
        pass

    return None

def get_readme(github_url: str) -> Optional[str]:
    """Downloads the README file from a GitHub repository.

    Args:
        github_url (str): The URL of the GitHub repository.

    Returns:
        Optional[str]: The content of the README file if found, otherwise None.
    
    Raises:
        ValueError: If the GitHub URL is invalid or if the GitHub API cannot be accessed.
    """
    readme_names = [
        'README.md', 'README.rst', 'README.txt', 'README',
        'readme.md', 'readme.rst', 'readme.txt', 'readme'
    ]

    # Parse the GitHub URL
    parsed_url = urlparse(github_url)
    path_parts = parsed_url.path.strip('/').split('/')

    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub URL. Expected format: 'https://github.com/owner/repo'")

    owner, repo = path_parts[0], path_parts[1]

    # Step 1: Get default branch using GitHub API
    api_url = f'https://api.github.com/repos/{owner}/{repo}'
    api_resp = requests.get(api_url)
    if api_resp.status_code != 200:
        raise ValueError(f"Could not access GitHub API: {api_resp.status_code}")

    default_branch = api_resp.json().get('default_branch', 'main')

    # Step 2: Try to download each possible README file
    for name in readme_names:
        raw_url = f'https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{name}'
        resp = requests.get(raw_url)
        if resp.status_code == 200:
            return resp.text
    return None

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