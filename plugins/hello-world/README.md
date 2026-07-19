# Hello World Plugin

A minimal AIOS plugin demonstrating the Plugin SDK.

## Structure

```
hello-world/
├── plugin.yaml          # Plugin manifest
├── plugin.py            # Plugin implementation
├── README.md            # Documentation
├── LICENSE              # License
├── requirements.txt     # Dependencies
├── icon.png             # Plugin icon
├── resources/           # Static resources
├── tools/               # Standalone tools
├── tests/               # Plugin-specific tests
└── assets/              # Media assets
```

## Capabilities

- `hello.say_hello` — Returns a friendly greeting
- `hello.echo` — Echoes back input

## Usage

Install the plugin by placing it in the AIOS plugins directory
(~/.aios/plugins/hello-world) and enabling it through the Plugin Manager.
