import os
import subprocess
from pathlib import Path

dir_path = Path(__file__).parent
mount_path = dir_path.parent
package_name = "jsgenerator"

def run_shell(command, shell=True, check=True, **kwargs):
    return subprocess.run(command, shell=shell, check=check, **kwargs)

def build_docker_container():
    print("BUILDING DOCKER IMAGE")
    run_shell(f"docker build --rm -t {package_name} -f {dir_path / 'Dockerfile'} {mount_path}")

def run_docker_container():
    print("RUNNING DOCKER CONTAINER")
    openai_api_key = os.getenv('OPENAI_API_KEY')
    assert openai_api_key is not None, "OpenAI API key environment variable was not set. Set it to a valid key to continue."
    
    run_shell(
        f"docker run --rm -it -e 'OPENAI_API_KEY={openai_api_key}' {package_name}",
        check=False
    )

# runs a docker container in the current directory
build_docker_container()
run_docker_container()