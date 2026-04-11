from jinja2 import Environment, meta


def extract_variables_from_text(text: str) -> set[str]:
    env = Environment()
    parsed = env.parse(text)
    return meta.find_undeclared_variables(parsed)
