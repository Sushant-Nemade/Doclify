import yaml
from pydantic import ValidationError

from doclify.schema.schema import ProjectConfig
from doclify.utils.file_utils import atomic_write, pipeline_lock, project_path


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str) or key in result:
            raise ValueError("Configuration has a duplicate or non-string key")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def load_config() -> ProjectConfig:
    path = project_path("doclify.yaml")
    if not path.is_file():
        raise ValueError("doclify.yaml not found; run doclify init first")
    if path.stat().st_size > 64_000:
        raise ValueError("Configuration exceeds 64 KB")
    try:
        content = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
        return ProjectConfig.model_validate(content)
    except (yaml.YAMLError, ValidationError, UnicodeError) as error:
        raise ValueError(
            "Invalid doclify.yaml shape or limits; review project, structure and llm settings"
        ) from error


def write_config(config: ProjectConfig) -> None:
    atomic_write(
        "doclify.yaml", yaml.safe_dump(config.model_dump(), sort_keys=False, allow_unicode=True)
    )


def update_config(model=None) -> None:
    with pipeline_lock():
        config = load_config()
        content = config.model_dump()
        content["llm"]["model"] = model
        try:
            updated = ProjectConfig.model_validate(content)
        except ValidationError as error:
            raise ValueError("Invalid model identifier") from error
        write_config(updated)
