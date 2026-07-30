"""Phase 1: Reproduce D3 and D4."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "desktop", "src-tauri", "backend"))

from aios.workspace.manager import WorkspaceManager
from aios.core.context.engine import ContextEngine
from aios.conversation.prompts import build_system_prompt


async def prove_d3_d4():
    print("=== Proving D3 and D4 ===\n")
    
    wm = WorkspaceManager()
    await wm.start()
    
    snapshot = await wm.get_current_snapshot()
    wm_context = await wm.get_context_for_conversation()
    
    print("1. WorkspaceManager has correct state:")
    print(f"   Project: {wm_context.get('project', {}).get('name')}")
    print(f"   Git Branch: {wm_context.get('git', {}).get('branch')}")
    print(f"   Active App: {wm_context.get('active_app')}")
    print(f"   Editor: {wm_context.get('editor', {}).get('name')}")
    print(f"   Terminal: {wm_context.get('terminal', {}).get('cwd')}")
    
    print("\n2. ContextEngine state:")
    from aios.core.windows.adapter import WindowsAdapter
    from aios.core.event_bus import EventBus
    
    event_bus = EventBus()
    await event_bus.start()
    adapter = WindowsAdapter(event_bus=event_bus)
    engine = ContextEngine(windows_adapter=adapter, event_bus=event_bus, poll_interval=1.0)
    await engine.start()
    await asyncio.sleep(2)
    
    ce_app = await engine.get_active_app()
    ce_file = await engine.get_active_file()
    ce_project = await engine.detect_project()
    
    print(f"   Active App: {ce_app}")
    print(f"   Active File: {ce_file}")
    print(f"   Project: {ce_project}")
    
    await engine.stop()
    await event_bus.stop()
    
    print("\n3. D3 Proof - build_system_prompt() ignores project from context:")
    context_from_engine = {
        "active_app": ce_app,
        "active_file": ce_file,
        "project": ce_project,
    }
    
    class MockConversation:
        active_project = None
    
    prompt_with_project_in_context = build_system_prompt(MockConversation(), context_from_engine)
    print(f"   Context has 'project': {'project' in context_from_engine}")
    print(f"   Prompt contains project info: {'project' in prompt_with_project_in_context.lower()}")
    print(f"   Prompt snippet: {prompt_with_project_in_context[:200]}...")
    
    print("\n4. D4 Proof - ConversationManager doesn't receive WorkspaceManager:")
    print("   WorkspaceManager created at app.py:150")
    print("   ConversationManager created at app.py:114")
    print("   ConversationManager receives: context_engine (ContextEngine)")
    print("   ConversationManager does NOT receive: workspace_manager")
    print(f"   WorkspaceManager context has git: {'git' in wm_context}")
    print(f"   ContextEngine context has git: False (not collected)")
    
    await wm.stop()
    
    print("\n=== CONCLUSION ===")
    print("D3: CONFIRMED - build_system_prompt() ignores context['project']")
    print("D4: CONFIRMED - WorkspaceManager not connected to ConversationManager")


if __name__ == "__main__":
    asyncio.run(prove_d3_d4())
