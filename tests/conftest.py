import importlib
import subprocess
import sys
import shutil


def _install_with_uv(package_spec: str):
    if shutil.which("uv") is None:
        return False
    try:
        subprocess.check_call(["uv", "run", sys.executable, "-m", "pip", "install", package_spec])
        importlib.invalidate_caches()
        return True
    except subprocess.CalledProcessError:
        return False


def pytest_sessionstart(session):
    try:
        import beancount  # noqa: F401
        return
    except ModuleNotFoundError as exc:
        # Try installing via uv if available
        if _install_with_uv("beancount>=2.3,<3.0"):
            try:
                import beancount  # noqa: F401
                return
            except ModuleNotFoundError:
                pass
        raise RuntimeError(
            "Missing dependency 'beancount'. Fix options:\n"
            " - Run tests via the Makefile so dependencies are synced: `make test`\n"
            " - Or install dev deps manually in your environment: `uv run python -m pip install -e '.[dev]'` or\n"
            "   python -m pip install -e '.[dev]' (if not using uv)\n"
        ) from exc
