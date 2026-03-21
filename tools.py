import shutil


def resolve_executable(name: str, *fallbacks: str) -> str:
    executable = shutil.which(name)
    if executable:
        return executable

    for fallback in fallbacks:
        if shutil.which(fallback):
            return shutil.which(fallback)
        try:
            with open(fallback):
                pass
        except OSError:
            continue
        return fallback

    raise FileNotFoundError(f"Required executable not found: {name}")
