import pytest
import tempfile
import os
import json
from aios.workspace.detector import ProjectDetector, FrameworkDetector
from aios.workspace.models import FrameworkType


@pytest.fixture
def detector():
    return ProjectDetector()


@pytest.mark.asyncio
async def test_detect_node_project(detector):
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = os.path.join(tmpdir, "package.json")
        with open(pkg, "w") as f:
            json.dump({"name": "test-project", "dependencies": {"react": "^18.0.0"}}, f)
        project = await detector.detect_project(tmpdir)
        assert project is not None
        assert project.name == "test-project"
        assert project.framework == FrameworkType.REACT


@pytest.mark.asyncio
async def test_detect_nextjs_project(detector):
    with tempfile.TemporaryDirectory() as tmpdir:
        pkg = os.path.join(tmpdir, "package.json")
        with open(pkg, "w") as f:
            json.dump({"name": "next-app", "dependencies": {"next": "^14.0.0", "react": "^18.0.0"}}, f)
        project = await detector.detect_project(tmpdir)
        assert project is not None
        assert project.framework == FrameworkType.NEXT_JS


@pytest.mark.asyncio
async def test_detect_python_project(detector):
    with tempfile.TemporaryDirectory() as tmpdir:
        req = os.path.join(tmpdir, "requirements.txt")
        with open(req, "w") as f:
            f.write("fastapi>=0.100.0\nuvicorn>=0.20.0\n")
        project = await detector.detect_project(tmpdir)
        assert project is not None
        assert project.framework == FrameworkType.FASTAPI
        assert project.language == "python"


@pytest.mark.asyncio
async def test_detect_rust_project(detector):
    with tempfile.TemporaryDirectory() as tmpdir:
        cargo = os.path.join(tmpdir, "Cargo.toml")
        with open(cargo, "w") as f:
            f.write("[package]\nname = \"test-rust\"\n")
        project = await detector.detect_project(tmpdir)
        assert project is not None
        assert project.framework == FrameworkType.RUST
        assert project.package_manager == "cargo"


@pytest.mark.asyncio
async def test_detect_no_project(detector):
    with tempfile.TemporaryDirectory() as tmpdir:
        project = await detector.detect_project(tmpdir)
        assert project is None


@pytest.mark.asyncio
async def test_framework_detector():
    fd = FrameworkDetector()
    fw = await fd.detect_framework(["package.json", "index.js"])
    assert fw == FrameworkType.NODE_JS

    fw = await fd.detect_framework(["requirements.txt", "app.py"])
    assert fw == FrameworkType.PYTHON

    fw = await fd.detect_framework(["Cargo.toml"])
    assert fw == FrameworkType.RUST

    fw = await fd.detect_framework(["go.mod"])
    assert fw == FrameworkType.GO

    fw = await fd.detect_framework(["README.md"])
    assert fw == FrameworkType.UNKNOWN


def test_detect_language():
    fd = FrameworkDetector()
    assert fd.detect_language(FrameworkType.NEXT_JS) == "typescript"
    assert fd.detect_language(FrameworkType.PYTHON) == "python"
    assert fd.detect_language(FrameworkType.RUST) == "rust"
    assert fd.detect_language(FrameworkType.GO) == "go"
