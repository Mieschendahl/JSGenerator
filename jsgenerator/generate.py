import re
import sys
from pathlib import Path
from typing import Optional, TextIO
from promptgpt import Prompter, GPT
from jsgenerator.utils import clone_repository, get_url, get_readme, get_main, create_dir, parse_examples, run_shell, filter_examples

IF = lambda x, y: y if x else ""

def generate_examples(package_name: str, extract: bool = True, generate: bool = True, fix: bool = True, work_path: str | Path = "__jsgenerator__", model_name: str = "gpt-4o-mini", log_file: Optional[TextIO] = sys.stdout, allow_injections: bool = False, only_var: bool = False) -> None:
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
        only_var: Whether to replace 'const' and 'let' with 'var' in the generated examples (necessary for certain run time analysis tools).
    """
    work_path = Path(work_path)
    github_url = get_url(package_name)
    repository_path = work_path / "repositories" / package_name
    clone_repository(github_url, repository_path)
    
    readme = None
    try:
        readme = get_readme(repository_path)
    except:
        pass
    
    main = None
    try:
        main = get_main(repository_path)
    except:
        pass
    
    assert readme is not None or main is not None
    
    if readme is not None:
        readme_path = work_path / "README" / f"{package_name}.md"
        create_dir(readme_path.parent, remove=False)
        readme_path.write_text(readme)

    if main is not None:
        main_path = work_path / "main" / f"{package_name}.js"
        create_dir(main_path.parent, remove=False)
        main_path.write_text(main)
    
    template_path = work_path / "playground_template"
    playground_path = work_path / "playground"
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
    
    if extract and readme is not None:
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
                + IF(
                    readme is not None,
                    f"\n\nHere is the readme of the package:\n```README\n{readme}\n```"
                )
                + IF(
                    main is not None,
                    f"\n\nHere is the main file of the package:\n```js\n{main}\n```"
                )
            )\
            .get_response()
        examples.extend(parse_examples(response))

    examples, failed_examples = filter_examples(examples, template_path, playground_path)
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
                + IF(
                    readme is not None,
                    f"\n\nHere is the readme of the package:\n```README\n{readme}\n```"
                )
                + IF(
                    main is not None,
                    f"\n\nHere is the main file of the package:\n```js\n{main}\n```"
                )
            )\
            .get_response()
        examples.extend(filter_examples(parse_examples(response), template_path, playground_path)[0])
        
    for i, example in enumerate(examples):
        if only_var:
            example = re.sub(r'\bconst\b', 'var', example)
            example = re.sub(r'\blet\b', 'var', example)
        file_path = base_path / f"example_{i}.js"
        file_path.write_text(example)