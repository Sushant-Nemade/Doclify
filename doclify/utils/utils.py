from importlib.resources import files


def get_prompt(prompt_name: str) -> str:
    if prompt_name not in {"batch_summary", "final_summary"}:
        raise ValueError("Unknown prompt name")
    return files("doclify").joinpath("prompts", f"{prompt_name}.txt").read_text(encoding="utf-8")
