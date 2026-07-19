"""Framework Detection Providers — detect project frameworks and commands."""

import os
from typing import Any
from aios.workspace.models import Project, FrameworkType
from aios.workspace.interfaces import IProjectDetector
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class PackageJsonDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        pkg = os.path.join(path, "package.json")
        if not os.path.exists(pkg):
            return None
        try:
            import json
            with open(pkg, "r") as f:
                data = json.load(f)

            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            scripts = data.get("scripts", {})

            framework = FrameworkType.NODE_JS
            language = "javascript"

            dep_names = list(deps.keys())
            dep_string = " ".join(dep_names).lower()

            if "next" in dep_string:
                framework = FrameworkType.NEXT_JS
            elif "react" in dep_string:
                framework = FrameworkType.REACT
            elif "vue" in dep_string:
                framework = FrameworkType.VUE
            elif "@angular" in dep_string:
                framework = FrameworkType.ANGULAR
            elif "flutter" or "react-native" in dep_string:
                if "react-native" in dep_string or "expo" in dep_string:
                    pass

            if framework == FrameworkType.NODE_JS:
                has_ts = "typescript" in dep_string or "ts-node" in dep_string
                language = "typescript" if has_ts else "javascript"

            pm = "pnpm" if os.path.exists(os.path.join(path, "pnpm-lock.yaml")) else \
                 "yarn" if os.path.exists(os.path.join(path, "yarn.lock")) else \
                 "npm"

            return Project(
                root_path=path,
                name=data.get("name", os.path.basename(path)),
                framework=framework,
                language=language,
                package_manager=pm,
                build_command=scripts.get("build", ""),
                test_command=scripts.get("test", ""),
                run_command=scripts.get("dev") or scripts.get("start", ""),
            )
        except Exception as e:
            logger.error("detector.package_json.failed", path=path, error=str(e))
            return None


class PythonDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        has_python = any(f in os.listdir(path) for f in
                         ["requirements.txt", "setup.py", "setup.cfg", "pyproject.toml", "Pipfile"])
        if not has_python:
            return None

        framework = FrameworkType.PYTHON
        language = "python"

        files = os.listdir(path)
        all_files_str = " ".join(f.lower() for f in files)
        names = self._read_config_files(path)

        if "fastapi" in names or "uvicorn" in all_files_str:
            framework = FrameworkType.FASTAPI
        elif "django" in names or os.path.exists(os.path.join(path, "manage.py")):
            framework = FrameworkType.DJANGO
        elif "flask" in names or "flask" in all_files_str:
            framework = FrameworkType.FLASK

        pm = "uv" if os.path.exists(os.path.join(path, "uv.lock")) else \
             "poetry" if os.path.exists(os.path.join(path, "poetry.lock")) else \
             "pipenv" if os.path.exists(os.path.join(path, "Pipfile.lock")) else \
             "pip"

        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=framework,
            language=language,
            package_manager=pm,
            build_command="",
            test_command="pytest" if os.path.exists(os.path.join(path, "pytest.ini")) or
                          os.path.exists(os.path.join(path, "pyproject.toml")) else "python -m pytest",
            run_command=self._detect_run_command(framework, path),
        )

    def _read_config_files(self, path: str) -> str:
        content = ""
        try:
            req = os.path.join(path, "requirements.txt")
            if os.path.exists(req):
                with open(req, "r") as f:
                    content += f.read().lower()
            toml = os.path.join(path, "pyproject.toml")
            if os.path.exists(toml):
                with open(toml, "r") as f:
                    content += f.read().lower()
        except Exception:
            pass
        return content

    def _detect_run_command(self, framework: FrameworkType, path: str) -> str:
        if framework == FrameworkType.FASTAPI:
            return "uvicorn main:app --reload"
        if framework == FrameworkType.DJANGO:
            return "python manage.py runserver"
        if framework == FrameworkType.FLASK:
            return "flask run"
        return "python main.py"


class RustDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        if not os.path.exists(os.path.join(path, "Cargo.toml")):
            return None
        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=FrameworkType.RUST,
            language="rust",
            package_manager="cargo",
            build_command="cargo build",
            test_command="cargo test",
            run_command="cargo run",
        )


class GoDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        if not os.path.exists(os.path.join(path, "go.mod")):
            return None
        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=FrameworkType.GO,
            language="go",
            package_manager="go mod",
            build_command="go build",
            test_command="go test ./...",
            run_command="go run .",
        )


class DotnetDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        csproj = [f for f in os.listdir(path) if f.endswith(".csproj")]
        sln = [f for f in os.listdir(path) if f.endswith(".sln")]
        if not csproj and not sln:
            return None
        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=FrameworkType.DOTNET,
            language="csharp",
            package_manager="nuget",
            build_command="dotnet build",
            test_command="dotnet test",
            run_command="dotnet run",
        )


class JavaDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        has_pom = os.path.exists(os.path.join(path, "pom.xml"))
        has_gradle = os.path.exists(os.path.join(path, "build.gradle"))
        if not has_pom and not has_gradle:
            return None
        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=FrameworkType.JAVA,
            language="java",
            package_manager="maven" if has_pom else "gradle",
            build_command="mvn compile" if has_pom else "gradle build",
            test_command="mvn test" if has_pom else "gradle test",
            run_command="mvn exec:java" if has_pom else "gradle run",
        )


class FlutterDetector(IProjectDetector):
    async def detect(self, path: str) -> Project | None:
        if not os.path.exists(os.path.join(path, "pubspec.yaml")):
            return None
        return Project(
            root_path=path,
            name=os.path.basename(path),
            framework=FrameworkType.FLUTTER,
            language="dart",
            package_manager="pub",
            build_command="flutter build",
            test_command="flutter test",
            run_command="flutter run",
        )
