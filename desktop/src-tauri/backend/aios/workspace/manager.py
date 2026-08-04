"""Workspace Manager — central orchestrator for workspace intelligence."""

import os
from datetime import datetime
from typing import Any

from aios.workspace.models import (
    Workspace, WorkspaceSnapshot, Application, Project, Repository, Editor, Terminal,
    FrameworkType, GitStatus, AppCategory,
)
from aios.workspace.sensors import ActiveWindowSensor, ProcessSensor
from aios.workspace.detector import ProjectDetector
from aios.workspace.git import GitCollector
from aios.workspace.cache import WorkspaceCache
from aios.workspace.watcher import WorkspaceWatcher
from aios.workspace.events import WorkspaceEventPublisher
from aios.workspace.repository import WorkspaceRepository
from aios.utils.logger import get_logger
from aios.error_intelligence import get_error_intelligence

logger = get_logger(__name__)


class WorkspaceManager:
    def __init__(self, event_bus: Any | None = None, memory: Any | None = None, db: Any | None = None):
        self._window_sensor = ActiveWindowSensor()
        self._process_sensor = ProcessSensor()
        self._project_detector = ProjectDetector()
        self._git = GitCollector()
        self._cache = WorkspaceCache(ttl_seconds=10)
        self._watcher = WorkspaceWatcher(poll_interval=2.0)
        self._events = WorkspaceEventPublisher(event_bus)
        self._repository = WorkspaceRepository(db)
        self._memory = memory
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        try:
            await self._window_sensor.start()
            await self._process_sensor.start()
        except Exception as e:
            try:
                svc = get_error_intelligence()
                svc.capture_exception(e, module="workspace.manager", message=f"Workspace start failed: {e}")
            except Exception:
                pass
            raise
        self._running = True
        logger.info("workspace_manager.started")

    async def stop(self) -> None:
        self._running = False
        await self._watcher.stop()
        await self._window_sensor.stop()
        await self._process_sensor.stop()
        logger.info("workspace_manager.stopped")

    async def get_current_snapshot(self) -> WorkspaceSnapshot:
        cached = await self._cache.get_snapshot()
        if cached:
            return cached
        return await self._build_snapshot()

    async def refresh(self) -> WorkspaceSnapshot:
        snapshot = await self._build_snapshot()
        await self._cache.update_snapshot(snapshot)
        await self._events.snapshot_created(snapshot)
        return snapshot

    async def _build_snapshot(self) -> WorkspaceSnapshot:
        window = await self._window_sensor.collect()
        process_data = await self._process_sensor.collect()

        active_app = Application(
            process_name=window.get("active_app", ""),
            window_title=window.get("active_window", ""),
            category=self._categorize_app(window.get("active_app", "")),
        )

        applications = process_data.get("applications", [])
        terminals = process_data.get("terminals", [])

        projects = await self._detect_projects(applications, window)
        repositories = await self._detect_repos(projects)
        editors = self._detect_editors(applications)
        term_list = self._build_terminals(terminals)

        return WorkspaceSnapshot(
            active_window=window.get("active_window", ""),
            active_application=active_app,
            applications=applications,
            projects=projects,
            repositories=repositories,
            editors=editors,
            terminals=term_list,
        )

    async def _detect_projects(self, applications: list, window: dict) -> list[Project]:
        paths = self._get_search_paths(applications, window)
        projects = []
        for path in paths:
            project = await self._project_detector.detect_project(path)
            if project and project not in projects:
                projects.append(project)
        return projects

    def _get_search_paths(self, applications: list, window: dict) -> list[str]:
        paths = set()
        cwd = os.getcwd()
        if os.path.isdir(cwd):
            paths.add(cwd)
        for app in applications:
            if hasattr(app, 'category') and app.category in {AppCategory.IDE, AppCategory.TERMINAL}:
                exe = getattr(app, 'executable', '')
                if exe:
                    p = os.path.dirname(exe)
                    if os.path.isdir(p):
                        paths.add(p)
        return list(paths)

    async def _detect_repos(self, projects: list[Project]) -> list[Repository]:
        repos = []
        for project in projects:
            if project.root_path:
                repo = await self._git.collect(project.root_path)
                if repo:
                    repos.append(repo)
        return repos

    def _detect_editors(self, applications: list) -> list[Editor]:
        editors = []
        for app in applications:
            if app.category == AppCategory.IDE:
                editor = Editor(
                    name=app.process_name.replace(".exe", ""),
                    pid=app.pid,
                    process_name=app.process_name,
                )
                editors.append(editor)
        return editors

    def _build_terminals(self, terminals: list) -> list[Terminal]:
        result = []
        for t in terminals:
            term = Terminal(
                cwd=os.getcwd(),
                shell=t.process_name.replace(".exe", ""),
                pid=t.pid,
                process_name=t.process_name,
            )
            result.append(term)
        return result

    def _categorize_app(self, name: str) -> AppCategory:
        known = {
            "code": AppCategory.IDE, "cursor": AppCategory.IDE, "windsurf": AppCategory.IDE,
            "rider": AppCategory.IDE, "idea": AppCategory.IDE, "devenv": AppCategory.IDE,
            "WindowsTerminal": AppCategory.TERMINAL, "cmd": AppCategory.TERMINAL,
            "powershell": AppCategory.TERMINAL, "pwsh": AppCategory.TERMINAL,
            "wt": AppCategory.TERMINAL, "git-bash": AppCategory.TERMINAL, "bash": AppCategory.TERMINAL,
            "chrome": AppCategory.BROWSER, "msedge": AppCategory.BROWSER, "firefox": AppCategory.BROWSER,
        }
        for key, cat in known.items():
            if key.lower() in name.lower():
                return cat
        return AppCategory.UNKNOWN

    async def get_projects(self) -> list[Project]:
        snapshot = await self.get_current_snapshot()
        return snapshot.projects

    async def get_applications(self) -> list[Application]:
        snapshot = await self.get_current_snapshot()
        return snapshot.applications

    async def get_git_repos(self) -> list[Repository]:
        snapshot = await self.get_current_snapshot()
        return snapshot.repositories

    async def get_editors(self) -> list[Editor]:
        snapshot = await self.get_current_snapshot()
        return snapshot.editors

    async def get_terminals(self) -> list[Terminal]:
        snapshot = await self.get_current_snapshot()
        return snapshot.terminals

    async def get_history(self, limit: int = 10) -> list[WorkspaceSnapshot]:
        return await self._cache.get_history(limit)

    async def get_context_for_conversation(self) -> dict:
        snapshot = await self.get_current_snapshot()
        context = {}
        if snapshot.projects:
            p = snapshot.projects[0]
            context["project"] = {"name": p.name, "framework": p.framework.value, "language": p.language}
        if snapshot.repositories:
            r = snapshot.repositories[0]
            context["git"] = {"branch": r.branch, "dirty": r.dirty, "ahead": r.ahead, "behind": r.behind}
        if snapshot.active_application:
            context["active_app"] = snapshot.active_application.process_name
        if snapshot.editors:
            e = snapshot.editors[0]
            context["editor"] = {"name": e.name, "active_file": e.active_file}
        if snapshot.terminals:
            t = snapshot.terminals[0]
            context["terminal"] = {"cwd": t.cwd, "shell": t.shell}
        context["active_window"] = snapshot.active_window
        return context
