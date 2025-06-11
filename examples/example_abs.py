from jsgenerator import generate_examples

# Generates examples under ./jsgenerator/examples/abs/basic/
generate_examples("abs", use_llm=False, model_name="gpt-4o-mini", work_path="jsgenerator")

# Generates examples under ./jsgenerator/examples/abs/llm/
generate_examples("abs", use_llm=True, model_name="gpt-4o-mini", work_path="jsgenerator")