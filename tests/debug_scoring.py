"""Debug planner scoring"""
import asyncio
import sys
sys.path.insert(0, r'E:\Eve_Ai\desktop\src-tauri\backend')

async def debug():
    from aios.core.capability_registry import CapabilityRegistry, _word_score
    from aios.core.tool_manager import ToolManager
    from aios.core.permission_manager import PermissionManager
    from aios.core.event_bus import EventBus

    eb = EventBus()
    pm = PermissionManager(event_bus=eb)
    cr = CapabilityRegistry()
    tm = ToolManager(permission_manager=pm, capability_registry=cr, event_bus=eb)

    from aios.tools.builtin import register_builtin_tools
    from aios.tools.system_tools import register_system_tools
    register_builtin_tools(tm)
    register_system_tools(tm, eb)
    await asyncio.sleep(0.3)

    request = "Create a file containing Hello from Eve"
    ranked = await cr.rank_for_task(request)
    
    print(f"Request: '{request}'")
    print(f"\nRanked capabilities ({len(ranked)}):")
    for cap, score in ranked:
        # Break down the score
        id_score = _word_score(cap.id, request) * 1.5
        name_score = _word_score(cap.name, request) * 1.2
        desc_score = _word_score(cap.description, request) * 1.0
        tag_score = max((_word_score(tag, request) for tag in cap.tags), default=0.0) * 0.8
        print(f"  {cap.id:20s} total={score:.3f}  id={id_score:.3f} name={name_score:.3f} desc={desc_score:.3f} tag={tag_score:.3f}")
    
    print(f"\nMIN_CAPABILITY_SCORE = 0.3")
    print(f"Capabilities above threshold: {sum(1 for _, s in ranked if s >= 0.3)}")
    print(f"Capabilities below threshold: {sum(1 for _, s in ranked if s < 0.3)}")

    await eb.stop()

asyncio.run(debug())
