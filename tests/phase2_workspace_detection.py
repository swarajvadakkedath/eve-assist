"""Phase 2: Test workspace detection."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "desktop", "src-tauri", "backend"))

from aios.workspace.manager import WorkspaceManager
from aios.core.context.engine import ContextEngine


async def test_workspace_manager():
    print("=== WorkspaceManager Test ===")
    wm = WorkspaceManager()
    await wm.start()
    
    snapshot = await wm.get_current_snapshot()
    
    print(f"Active Window: {snapshot.active_window}")
    print(f"Active App: {snapshot.active_application.process_name if snapshot.active_application else 'None'}")
    print(f"Active App Category: {snapshot.active_application.category.value if snapshot.active_application else 'None'}")
    
    print(f"\nProjects ({len(snapshot.projects)}):")
    for p in snapshot.projects:
        print(f"  - {p.name} ({p.framework.value}) at {p.root_path}")
    
    print(f"\nRepositories ({len(snapshot.repositories)}):")
    for r in snapshot.repositories:
        print(f"  - {r.branch} (dirty={r.dirty}, ahead={r.ahead}, behind={r.behind})")
        print(f"    Remote: {r.remote}")
    
    print(f"\nEditors ({len(snapshot.editors)}):")
    for e in snapshot.editors:
        print(f"  - {e.name} (PID={e.pid})")
    
    print(f"\nTerminals ({len(snapshot.terminals)}):")
    for t in snapshot.terminals:
        print(f"  - {t.shell} (CWD={t.cwd})")
    
    context = await wm.get_context_for_conversation()
    print(f"\nConversation Context: {context}")
    
    await wm.stop()


async def test_context_engine():
    print("\n=== ContextEngine Test ===")
    from aios.core.windows.adapter import WindowsAdapter
    from aios.core.event_bus import EventBus
    
    event_bus = EventBus()
    await event_bus.start()
    
    adapter = WindowsAdapter(event_bus=event_bus)
    engine = ContextEngine(windows_adapter=adapter, event_bus=event_bus, poll_interval=1.0)
    await engine.start()
    
    await asyncio.sleep(2)
    
    app = await engine.get_active_app()
    file = await engine.get_active_file()
    project = await engine.detect_project()
    
    print(f"Active App: {app}")
    print(f"Active File: {file}")
    print(f"Project: {project}")
    
    await engine.stop()
    await event_bus.stop()


async def main():
    await test_workspace_manager()
    await test_context_engine()


if __name__ == "__main__":
    asyncio.run(main())
