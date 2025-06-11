import re
import sys
from pathlib import Path
from typing import Optional, TextIO
from promptgpt import Prompter, GPT
from jsgenerator.utils import get_url, get_readme, create_dir, parse_examples, run_shell, filter_examples

def generate_examples(package_name: str, extract: bool = True, generate: bool = True, fix: bool = True, work_path: str | Path = "__jsgenerator__", model_name: str = "gpt-4o-mini", log_file: Optional[TextIO] = sys.stdout, allow_injections: bool = False, no_const: bool = False) -> None:
    """Generates examples for a given npm package.

    This function extracts code examples from the README of the specified npm package,
    generates additional examples using a language model, and saves them to a specified
    directory. It can also fix any failed examples if requested.

    Args:
        package_name: The name of the npm package to generate examples for.
        extract: Whether to extract existing examples from the README.
        generate: Whether to generate new examples using a language model.
        fix: Whether to attempt to fix any failed examples.
        work_path: The directory where the generated examples will be saved.
        model_name: The name of the language model to use for generation.
        log_file: The file to log messages to.
        allow_injections: Whether to allow code injections in the generated examples.
        no_const: Whether to replace 'const' with 'var' in the generated examples.
    """
    github_url = get_url(package_name)
    if github_url is None:
        return None
    
    readme = get_readme(github_url)
    if readme is None:
        return None
    
    work_path = Path(work_path)
    readme_path = work_path / "READMEs" / f"{package_name}.md"
    create_dir(readme_path.parent, remove=False)
    readme_path.write_text(readme)
    
    template_path = work_path / "template"
    project_path = work_path / "project"
    create_dir(template_path)
    run_shell(f"npm install {package_name}", cwd=template_path)
    
    base_path = work_path / "examples" / package_name
    create_dir(base_path)

    model = GPT()\
        .set_cache(f"__promptgpt__/{model_name}")\
        .configure(model=model_name, temperature=0)
    
    prompter = Prompter(
            model=model,
            log_file=log_file,
            allow_injections=allow_injections
        )
    
    examples: list[str] = []
    
    if extract:
        pattern = r"```(?:js|javascript)\n(.*?)```"
        code_blocks = re.findall(pattern, readme, flags=re.DOTALL)
        examples.extend([match.strip() for match in code_blocks])

    if generate:
        response = prompter.copy()\
            .add_message("You are a Javscript/Node package expert.", role="developer")\
            .add_message(
                f"Please look at the readme of the npm package \"{package_name}\" and generate a list of use case examples for this package."
                f"\nOnly respond with the list of examples."
                f"\nEach example should start with ```js and end with ```."
                f"\nEach example should be independently executable via Node."
                f"\nEach example should be meaningfully different."
                f"\nHere is the readme of the package:\n```README\n{readme}\n```"
            )\
            .get_response()
        examples.extend(parse_examples(response))

    examples, failed_examples = filter_examples(examples, template_path, project_path)
    if fix and len(failed_examples) > 0:
        response = prompter.copy()\
            .add_message("You are a Javscript/Node package expert.", role="developer")\
            .add_message(
                f"I am trying to run some use case examples for the npm package \"{package_name}\" but Node raised and error."
                f"\nPlease try to fix these examples."
                f"\nOnly respond with the list of fixed examples."
                f"\nEach example should start with ```js and end with ```."
                f"\nEach example should be independently executable via Node."
                + "".join(
                    f"\n\nExample {i+1}:\n```js\n{example}\n```\n\nError {i+1}:\n```bash\n{error}\n```"
                    for i, (example, error) in enumerate(failed_examples)
                )
                + f"\nHere is the readme of the package:\n```README\n{readme}\n```"
            )\
            .get_response()
        examples.extend(filter_examples(parse_examples(response), template_path, project_path)[0])
        
    for i, example in enumerate(examples):
        if no_const:
            example = re.sub(r'\bconst\b', 'var', example)
        file_path = base_path / f"example_{i}.js"
        file_path.write_text(example)