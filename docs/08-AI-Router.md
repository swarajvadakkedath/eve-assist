# AI Router

**Document ID:** 08-AI-Router  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

The AI Router is responsible for abstracting AI provider interactions, routing requests to the appropriate provider, handling failover, and optimizing cost and performance.

## 2. Architecture

```mermaid
graph TB
    subgraph "AI Router"
        AR[Router Core]
        PM[Provider Manager]
        RM[Rate Limiter]
        CM[Cost Monitor]
        FM[Failover Manager]
    end

    subgraph "Providers"
        OAI[OpenAI]
        ANT[Anthropic]
        OLL[Ollama - Local]
        CUS[Custom Provider]
    end

    subgraph "Strategies"
        LS[Latency Strategy]
        CS[Cost Strategy]
        PS[Performance Strategy]
        FS[Fallback Strategy]
    end

    AR --> LS
    AR --> CS
    AR --> PS
    AR --> FS
    LS --> OAI
    LS --> ANT
    CS --> OLL
    PS --> OAI
    PS --> ANT
    FS --> OLL
```

## 3. Provider Abstraction

```python
class AIProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] = None) -> AIResponse
    @abstractmethod
    async def chat_stream(self, messages: list[dict], tools: list[dict] = None) -> AsyncIterator[str]
    @abstractmethod
    async def embed(self, text: str) -> list[float]
    @abstractmethod
    async def health_check(self) -> bool
    @property
    @abstractmethod
    def model(self) -> str
    @property
    @abstractmethod
    def capabilities(self) -> set[str]
```

## 4. Routing Strategy

```mermaid
graph TD
    R[Request] --> E{Evaluate}
    E -->|Simple Query| C[Cost Strategy]
    E -->|Complex Task| P[Performance Strategy]
    E -->|Latency Sensitive| L[Latency Strategy]
    E -->|Provider Down| F[Failover Strategy]

    C --> OLL[Ollama - Local]
    P --> OAI[OpenAI GPT-4]
    L --> ANT[Anthropic Claude]
    F --> ALT[Alternate Provider]
```

## 5. Failover Strategy

```mermaid
graph TD
    R[Request] --> P1{Primary Available?}
    P1 -->|Yes| Primary[Execute]
    P1 -->|No| F1{Fallback 1 Available?}
    F1 -->|Yes| Fallback1[Execute]
    F1 -->|No| F2{Fallback 2 Available?}
    F2 -->|Yes| Fallback2[Execute]
    F2 -->|No| Error[Return Error]
```

## 6. Rate Limiting

| Provider | Requests/min | Tokens/min | Concurrent |
|----------|-------------|------------|------------|
| OpenAI GPT-4 | 20 | 40,000 | 3 |
| OpenAI GPT-3.5 | 60 | 90,000 | 6 |
| Anthropic Claude | 30 | 50,000 | 4 |
| Ollama (local) | Unlimited | Unlimited | 10 |

## 7. Cost Optimization

```mermaid
graph LR
    R[Request] --> A{Analyze Complexity}
    A -->|Simple| L[Local Model]
    A -->|Medium| C[GPT-3.5/Claude Haiku]
    A -->|Complex| P[GPT-4/Claude Sonnet]
    A -->|Vision| V[GPT-4 Vision]
    L -->|Cost: $0| Done
    C -->|Cost: Low| Done
    P -->|Cost: High| Done
    V -->|Cost: High| Done
```

## 8. Model Capabilities

| Capability | GPT-4 | GPT-3.5 | Claude 3 | Local |
|------------|-------|---------|----------|-------|
| Chat | ✓ | ✓ | ✓ | ✓ |
| Tools | ✓ | ✓ | ✓ | Limited |
| Vision | ✓ | ✗ | ✓ | ✗ |
| Long context | 128K | 16K | 200K | 8K |
| Code | ✓ | ✓ | ✓ | Limited |
| Reasoning | ✓ | Basic | ✓ | Basic |

## 9. Public Interface

```python
class AIRouter:
    async def route(self, request: AIRequest) -> AIResponse
    async def route_stream(self, request: AIRequest) -> AsyncIterator[str]
    async def register_provider(self, provider: AIProvider) -> None
    async def health_check(self) -> dict[str, bool]
    def get_capabilities(self) -> dict[str, list[str]]
```

## 10. Implementation Notes

- Providers are loaded from configuration
- Health checks run every 30 seconds
- Rate limiting is per-provider and per-user
- Cost tracking is persisted to SQLite
- Failover is automatic and transparent
