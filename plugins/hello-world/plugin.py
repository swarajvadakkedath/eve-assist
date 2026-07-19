"""Hello World — minimal AIOS plugin example."""

from aios.plugins.sdk import AIOSPlugin
from aios.plugins.models import PluginResult, PluginCapability


class HelloWorldPlugin(AIOSPlugin):
    async def initialize(self):
        self._greeting = "Hello"
        self.log_info("HelloWorld plugin initializing")
        config = await self.get_setting("greeting", "Hello")
        self._greeting = config

    async def register(self):
        self.log_info("HelloWorld plugin registering capabilities")

        say_hello_cap = PluginCapability(
            id="hello.say_hello",
            name="Say Hello",
            description="Returns a friendly greeting",
            permission_level=0,
            parameters={
                "name": {
                    "type": "string",
                    "description": "Name to greet",
                    "required": False,
                }
            },
            returns={
                "type": "string",
                "description": "The greeting message",
            },
        )

        echo_cap = PluginCapability(
            id="hello.echo",
            name="Echo",
            description="Echoes back the input",
            permission_level=0,
            parameters={
                "message": {
                    "type": "string",
                    "description": "Message to echo",
                    "required": True,
                }
            },
            returns={
                "type": "string",
                "description": "The echoed message",
            },
        )

        await self.register_capability(say_hello_cap)
        await self.register_capability(echo_cap)

    async def start(self):
        self.log_info("HelloWorld plugin started")

    async def health(self):
        return {"status": "alive", "greeting": self._greeting}

    async def stop(self):
        self.log_info("HelloWorld plugin stopping")

    async def shutdown(self):
        self.log_info("HelloWorld plugin shutting down")

    async def dispose(self):
        self.log_info("HelloWorld plugin disposed")


async def execute(params: dict) -> PluginResult:
    action = params.get("action", "hello")
    if action == "hello":
        name = params.get("name", "World")
        return PluginResult(success=True, data={"message": f"Hello, {name}!"})
    elif action == "echo":
        message = params.get("message", "")
        return PluginResult(success=True, data={"echo": message})
    return PluginResult(success=False, error=f"Unknown action: {action}")