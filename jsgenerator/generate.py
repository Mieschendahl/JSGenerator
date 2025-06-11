import re
import sys
from pathlib import Path
from typing import Optional, TextIO
from promptgpt import Prompter, GPT
from jsgenerator.utils import get_url, get_readme, create_dir, parse_examples, run_shell, filter_examples

def generate_examples(package_name: str, use_llm: bool = False, work_path: str | Path = "__jsgenerator__", model_name: str = "gpt-4o-mini", log_file: Optional[TextIO] = sys.stdout, allow_injections: bool = False, no_const: bool = False) -> None:
    github_url = get_url(package_name)
    if github_url is None:
        return None
    
    readme = get_readme(github_url)
    if readme is None:
        return None
    
    work_path = Path(work_path)
    template_path = work_path / "template"
    project_path = work_path / "project"
    create_dir(template_path)
    run_shell(f"npm install {package_name}", cwd=template_path)
    
    use_llm_str = ("llm" if use_llm else "basics")
    base_path = work_path/ "examples" / package_name / use_llm_str
    create_dir(base_path, remove=True)
    
    if not use_llm: 
        pattern = r"```(?:\w+)?\n(.*?)```"
        code_blocks = re.findall(pattern, readme, flags=re.DOTALL)
        examples = [match.strip() for match in code_blocks]
    else:
        model = GPT()\
            .set_cache(f"__promptgpt__/{model_name}")\
            .configure(model=model_name, temperature=0)
        
        prompter = Prompter(
                model=model,
                log_file=log_file,
                allow_injections=allow_injections
            )

        response = prompter\
            .add_message("You are a Javscript/Node package expert.", role="developer")\
            .add_message(
                f"Please look at the readme of the npm package {package_name} and generate a list of use case examples for this package."
                f"\nOnly respond with the possibly empty list of examples."
                f"\nEach example should start with ```js and end with ```."
                f"\nEach example should be independently executable via Node."
                f"\nEach example should be meaningfully different."
                f"\nHere is the readme of the package:\n\n{readme}"
            )\
            .get_response()
        examples = parse_examples(response)

    examples = filter_examples(examples, template_path, project_path)[0]
    for i, example in enumerate(examples):
        if no_const:
            example = re.sub(r'\bconst\b', 'var', example)
        file_path = base_path / f"example_{i}.js"
        file_path.write_text(example)