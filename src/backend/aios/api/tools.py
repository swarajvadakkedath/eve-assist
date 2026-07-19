"""Tool API routes."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["tools"])


class ExecuteRequest(BaseModel):
    tool_id: str
    params: dict = {}


@router.get("/tools")
async def list_tools(req: Request, category: str = None):
    tm = req.app.state.tool_manager
    tools = await tm.list_tools(category)
    return {
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "permission_level": int(t.permission_level),
                "category": t.category,
                "parameters": t.parameters,
                "capabilities": t.capabilities,
            }
            for t in tools
        ]
    }


@router.post("/tools/execute")
async def execute_tool(req: Request, body: ExecuteRequest):
    tm = req.app.state.tool_manager
    result = await tm.execute(body.tool_id, body.params)
    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "duration": result.duration,
    }


@router.get("/tools/{tool_id}")
async def get_tool(req: Request, tool_id: str):
    tm = req.app.state.tool_manager
    tool = await tm.get_tool(tool_id)
    if not tool:
        return {"error": "Tool not found"}, 404
    return {
        "id": tool.id,
        "name": tool.name,
        "description": tool.description,
        "permission_level": int(tool.permission_level),
        "category": tool.category,
        "parameters": tool.parameters,
        "returns": tool.returns,
        "capabilities": tool.capabilities,
    }


@router.get("/tools/search/{query}")
async def search_tools(req: Request, query: str):
    tm = req.app.state.tool_manager
    tools = await tm.search_tools(query)
    return {
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
            }
            for t in tools
        ]
    }


@router.get("/tools/categories")
async def list_tool_categories(req: Request):
    tm = req.app.state.tool_manager
    all_tools = await tm.list_tools()
    categories: dict[str, list] = {}
    for t in all_tools:
        cat = t.category or "general"
        categories.setdefault(cat, []).append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "permission_level": int(t.permission_level),
            "parameters": t.parameters,
            "requires_confirmation": t.requires_confirmation,
            "tags": t.tags,
            "capabilities": t.capabilities,
        })
    return {"categories": categories, "total_tools": len(all_tools)}


@router.get("/tools/by-category/{category}")
async def list_tools_by_category(req: Request, category: str):
    tm = req.app.state.tool_manager
    all_tools = await tm.list_tools()
    filtered = [t for t in all_tools if t.category == category]
    return {
        "category": category,
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "permission_level": int(t.permission_level),
                "parameters": t.parameters,
                "returns": t.returns,
                "tags": t.tags,
                "capabilities": t.capabilities,
            }
            for t in filtered
        ],
        "count": len(filtered),
    }
