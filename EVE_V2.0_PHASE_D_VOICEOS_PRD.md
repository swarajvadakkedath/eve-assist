# EVE v2.0 — Phase D: VoiceOS+

**Product Requirements & Architecture**

**Date:** August 2026
**Status:** DESIGN
**Frozen Kernel:** Phase C (v2.0-alpha)
**Tests:** 464/464 passing
**Principle:** Voice becomes the primary interface. Chat becomes secondary.

---

## Section 1 — Vision

### Why VoiceOS+

Voice is how humans naturally communicate. Every other interface — keyboard, mouse, touch — is a translation layer between intent and action. Voice removes the translation. The user thinks, speaks, and the AI acts.

EVE already has a voice session manager, STT/TTS, and a personality layer. But today, voice is a secondary input method — the user must open the app, click the microphone, and speak into a chat box. VoiceOS+ inverts this: EVE is always listening, always aware, always ready. The user never touches the keyboard unless they choose to.

### Why Voice-First

| Paradigm | User Action | EVE Action |
|----------|------------|------------|
| Chat-first | Open app → Type → Read response | Process → Generate text |
| Voice-first | Speak → Listen to response | Detect → Transcribe → Reason → Speak |

Voice-first eliminates the friction of opening an application, navigating to a text field, and typing. For desktop users, voice is faster for most tasks. For hands-busy scenarios (cooking, driving, coding), voice is the only option.

### How VoiceOS Differs from Voice Assistants

| Feature | Siri/Alexa/Google | EVE VoiceOS+ |
|---------|-------------------|--------------|
| Wake word | "Hey Siri" / "Alexa" | Custom, local, configurable |
| Conversation | One command at a time | Multi-turn continuous dialogue |
| Interruptions | Not supported | Natural mid-sentence interruption |
| Context | Stateless per command | Full ExecutionContext carried across turns |
| Personality | Generic assistant | EVE persona (warm, professional, technically capable) |
| Capabilities | Limited to vendor ecosystem | Full desktop, code, files, browser, memory |
| Privacy | Cloud-only processing | Local wake word, optional cloud STT |
| Streaming | None | Word-level TTS streaming |
| Memory | None | Lifelong memory across sessions |
| Multi-provider | Single provider | Smart Router (17 providers, capability-driven) |

### Relationship to Hermes

Hermes provides the reasoning engine. When EVE receives a voice command, the pipeline is:

```
Voice → STT → Text → Conversation Pipeline → Hermes (reasoning) → Response → TTS → Voice
```

Hermes is invisible. The user never knows Hermes exists. EVE attributes all responses, all actions, all intelligence to itself. Hermes is the brain; EVE is the body. VoiceOS+ makes the body speak.

### Relationship to EVE

VoiceOS+ is EVE's voice layer. It sits on top of the frozen kernel:

- **Context Engine** provides environmental awareness (what the user is looking at, working on, selected)
- **Smart Router** selects the best provider for voice-optimized responses
- **Memory System** maintains conversation history and lifetime knowledge
- **Tool System** executes actions via voice commands
- **Recovery System** handles voice failures transparently
- **Identity Layer** ensures all responses are attributed to EVE

VoiceOS+ does not replace any kernel component. It extends the voice layer that already exists.

---

## Section 2 — Goals

### Primary Goals

1. **Wake word detection** — EVE responds to a configurable wake phrase, always listening locally
2. **Continuous conversation** — Multiple turns without re-waking; natural dialogue flow
3. **Natural interruptions** — User can interrupt EVE mid-sentence; EVE stops and listens
4. **Streaming voice** — Word-level TTS playback; user hears EVE think in real-time
5. **Desktop overlay** — Floating visual indicator showing EVE's state (listening, thinking, speaking)
6. **Full context** — Voice commands automatically receive ExecutionContext; no manual context selection
7. **Low latency** — End-to-end response under 2 seconds for simple queries

### Secondary Goals

1. **Push-to-talk** — Keyboard shortcut to activate without wake word
2. **Multiple conversations** — Switch between topic contexts via voice
3. **Code by voice** — Dictate code, run commands, navigate files
4. **Design by voice** — Describe UI changes, generate designs
5. **Proactive suggestions** — EVE offers help based on context (opt-in)
6. **Multi-language** — Support for multiple spoken languages
7. **Voice cloning** — Custom voice profiles (future)

### Non-Goals

1. **Replacing chat** — Chat remains available for complex, multi-file tasks
2. **Real-time translation** — Not in Phase D scope
3. **Emotion detection** — Not in Phase D scope (voice tone analysis is future)
4. **Multi-user conversations** — Single user only
5. **Phone/call integration** — Not in Phase D scope
6. **Music/audio playback** — Not in Phase D scope

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Wake detection accuracy | >95% | False positive rate <1% |
| STT accuracy (quiet room) | >97% | Word error rate |
| End-to-end latency (simple) | <2s | Voice-in to voice-out |
| End-to-end latency (complex) | <5s | Voice-in to voice-out |
| Conversation continuity | >80% | Successful multi-turn without re-wake |
| Interruption response | <500ms | EVE stops speaking after user interrupts |
| User satisfaction | >4.0/5 | Post-session survey |
| CPU usage (idle) | <2% | Continuous listening overhead |
| RAM usage | <150MB | Voice subsystem total |
| Battery impact | <5%/hour | Laptop battery drain |

---

## Section 3 — Voice User Experience

### 3.1 — Wake Word

The user says the wake phrase. EVE responds with a subtle visual cue (overlay appears) and a brief audio acknowledgment (optional, configurable). EVE is now listening.

**Examples:**
- "Hey EVE" → Overlay appears, soft chime, listening indicator
- "EVE" → Same, configurable sensitivity
- Custom phrase → User-defined in settings

**Behavior:**
- Wake phrase detected → Listening state begins
- No wake phrase → Background noise ignored, no processing
- Multiple wake phrases supported simultaneously
- Sensitivity adjustable per phrase

### 3.2 — Push-to-Talk

User holds a keyboard shortcut (default: Ctrl+Space) while speaking. Release to send. No wake word needed.

**Use case:** Noisy environments, quick commands, keyboard-centric workflows.

**Behavior:**
- Key down → Listening state begins (overlay shows microphone)
- Key up → Processing begins
- No timeout while key held
- Visual indicator shows recording duration

### 3.3 — Continuous Conversation

After EVE responds, the conversation continues. The user speaks naturally without re-waking.

**Example:**
```
User: "Hey EVE, what's the weather?"
EVE: "It's 72°F and sunny in San Francisco."
User: "Will it rain tomorrow?"
EVE: "No rain expected tomorrow. High of 75°."
User: "What about this weekend?"
EVE: "Saturday looks clear. Sunday has a 30% chance of showers."
User: "Thanks."
EVE: "You're welcome."
```

**Behavior:**
- After EVE finishes speaking, listening resumes automatically
- Conversation timeout: 10 seconds of silence → return to idle (configurable)
- Context carries across all turns in a conversation
- User can say "never mind" or "done" to end explicitly

### 3.4 — Interruptions

The user can interrupt EVE mid-sentence. EVE stops speaking immediately and listens.

**Example:**
```
EVE: "The weather tomorrow will be—"
User: "Actually, what's the forecast for Saturday?"
EVE: "Saturday will be clear with a high of 75°."
```

**Behavior:**
- User voice detected during EVE speech → EVE stops within 500ms
- Partial sentence discarded
- User's new input processed immediately
- No apology for interruption (natural conversation)
- EVE remembers the interrupted context for follow-up

### 3.5 — Natural Pauses

The user pauses mid-thought. EVE waits.

**Example:**
```
User: "Hey EVE, open the file... um... the one I was working on yesterday."
EVE: "You mean main.py in the eve-ai project?"
User: "Yes, that one."
```

**Behavior:**
- 2-second silence → EVE holds, no response
- 5-second silence → EVE confirms: "Still listening..."
- 10-second silence → EVE ends listening, processes what was said
- Pauses within a sentence do not trigger completion

### 3.6 — Follow-up Questions

EVE maintains context for follow-ups. The user can reference previous responses naturally.

**Example:**
```
User: "What's the capital of France?"
EVE: "Paris."
User: "How many people live there?"
EVE: "Paris has approximately 2.1 million people in the city proper,
     and 12.2 million in the metro area."
User: "Is it bigger than London?"
EVE: "No. London's metro area is about 9.5 million,
     but the city proper is smaller than Paris."
```

**Behavior:**
- Pronouns resolved against conversation history
- "It", "there", "that", "the same one" all resolve contextually
- Follow-ups work across voice and text (if user switches to chat)

### 3.7 — Conversation Timeout

Conversations end after inactivity.

**Timeouts:**
- 10 seconds of silence → "Are you still there?" (spoken)
- 20 seconds of silence → End conversation, return to idle
- User says "never mind" / "done" / "thanks" → Immediate end
- User wakes again → New conversation starts

**Behavior:**
- Timeout is configurable (5-60 seconds)
- Warning spoken at 50% of timeout
- Timer resets on any user speech
- Visual indicator shows timeout countdown in overlay

### 3.8 — Multiple Conversations

Users can switch between conversation contexts.

**Example:**
```
User: "Hey EVE, let's talk about the deploy."
EVE: "Sure, what do you need?"
User: "Actually, switch to the other project."
EVE: "Switching to eve-ai. What do you need?"
```

**Behavior:**
- "Switch to [project/topic]" → New conversation context
- Previous conversation paused (not lost)
- User can return: "Go back to the deploy conversation"
- Maximum active conversations: 5 (configurable)

### 3.9 — Desktop Commands

EVE controls the desktop via voice.

**Examples:**
```
User: "Open Visual Studio Code"
User: "Switch to Chrome"
User: "Take a screenshot"
User: "What's on my screen?"
User: "Scroll down"
User: "Copy this text"
User: "Run the tests"
User: "Commit these changes"
```

**Behavior:**
- Desktop commands routed through ToolMediator
- Confirmation required for destructive actions (delete, commit, deploy)
- Confirmation optional for safe actions (open, switch, copy)
- Tool execution visible in overlay timeline

### 3.10 — Coding Workflows

EVE assists with code via voice.

**Examples:**
```
User: "What function am I looking at?"
EVE: "You're looking at the send_message function in manager.py.
     It handles non-streaming conversation."

User: "Add a parameter called timeout with a default of 30."
EVE: "Added timeout=30 to send_message. Want me to update the callers?"

User: "Run the tests"
EVE: "Running pytest... 464 tests passed."
```

**Behavior:**
- Code context from SelectionContext and WorkspaceContext
- Code edits go through ToolMediator (EditFile tool)
- Code review via voice requires confirmation
- Git operations via voice require confirmation

### 3.11 — Design Workflows

EVE assists with design via voice.

**Examples:**
```
User: "What does this page look like?"
EVE: "The dashboard shows 4 metric cards, a chart, and a table.
     It uses a dark theme with blue accents."

User: "Make the header bigger"
EVE: "Increased the header font size from 24px to 32px.
     Want me to show you the result?"
```

**Behavior:**
- Vision context from BrowserContext and SelectionContext
- Design edits routed through appropriate tools
- Preview via screenshot capture
- Confirmation for visual changes

---

## Section 4 — Conversation Lifecycle

### State Diagram

```
                    +-----------------+
                    |                 |
        +---------->|      IDLE       |<----------+
        |           |                 |           |
        |           +--------+--------+           |
        |                    |                    |
        |     Wake word /    |    Timeout /       |
        |     Push-to-talk   |    "Done"          |
        |                    v                    |
        |           +-----------------+           |
        |           |                 |           |
        |           |    LISTENING    |           |
        |           |                 |           |
        |           +--------+--------+           |
        |                    |                    |
        |     VAD silence /  |    User speaks     |
        |     Key release    |    (interrupt)      |
        |                    v                    |
        |           +-----------------+           |
        |           |                 |           |
        |           |    THINKING     |-----------+
        |           |                 |           |
        |           +--------+--------+           |
        |                    |                    |
        |     LLM response / |    Tool execution  |
        |     TTS ready      |                    |
        |                    v                    |
        |           +-----------------+           |
        |           |                 |           |
        +-----------|    SPEAKING     |-----------+
                    |                 |
                    +--------+--------+
                             |
                    TTS complete /
                    User interrupt
                             |
                             v
                    +-----------------+
                    |                 |
                    |   FOLLOW-UP     |
                    |                 |
                    +--------+--------+
                             |
                    User speaks /
                    Timeout
                             |
                             v
                      (back to IDLE or LISTENING)
```

### State Descriptions

| State | Entry Condition | Behavior | Exit Condition |
|-------|----------------|----------|----------------|
| IDLE | Startup / timeout / "done" | Background listening for wake word only | Wake word detected, push-to-talk pressed |
| LISTENING | Wake word / push-to-talk | Capturing audio, streaming to STT | VAD silence / key release / completion |
| THINKING | User speech complete | Processing through pipeline, LLM inference, tool execution | LLM response ready, TTS ready |
| SPEAKING | TTS ready | Playing audio, showing overlay animation | TTS complete / user interrupt |
| FOLLOW-UP | Speaking complete | Waiting for user response, conversation context active | User speaks / timeout |

### Transitions

| From | To | Trigger | Action |
|------|----|---------|--------|
| IDLE → LISTENING | Wake word detected | Start audio capture, show overlay |
| IDLE → LISTENING | Push-to-talk key down | Start audio capture, show overlay |
| LISTENING → THINKING | VAD silence (2s) | Send audio to STT, begin processing |
| LISTENING → THINKING | Push-to-talk key up | Send audio to STT, begin processing |
| LISTENING → IDLE | Timeout (10s silence) | Cancel capture, hide overlay |
| THINKING → SPEAKING | TTS audio ready | Begin playback, show speaking animation |
| THINKING → IDLE | Error (provider failure) | Show error, return to idle |
| SPEAKING → FOLLOW-UP | TTS complete | Begin follow-up listening window |
| SPEAKING → LISTENING | User interrupt detected | Stop TTS, begin listening |
| FOLLOW-UP → LISTENING | User speaks | Resume listening |
| FOLLOW-UP → IDLE | Timeout (10s silence) | End conversation, hide overlay |

### Invariants

- IDLE is the only state where wake word detection runs at full power
- LISTENING always has a maximum duration (configurable, default 30s)
- THINKING always has a maximum duration (configurable, default 30s)
- SPEAKING can be interrupted at any point
- FOLLOW-UP window is always limited (configurable, default 10s)
- Any state can return to IDLE via user command ("stop", "done", "never mind")

---

## Section 5 — Wake Word

### Engine Abstraction

The wake word engine is an abstract interface. Multiple implementations can be swapped:

| Engine | Type | Accuracy | Latency | Power | Cost |
|--------|------|----------|---------|-------|------|
| Porcupine (Picovoice) | Local, on-device | High | <100ms | Low | Free tier + paid |
| OpenWakeWord | Local, on-device | Medium | <200ms | Low | Free, open source |
| Snowboy (deprecated) | Local, on-device | Medium | <150ms | Low | Free, open source |
| Custom ONNX | Local, on-device | Varies | Varies | Varies | Free |
| Cloud-based | Cloud API | High | <300ms | Medium | Paid |

**Design decision:** Default engine is OpenWakeWord (free, open source). Users can upgrade to Porcupine for higher accuracy.

### Local Inference

Wake word detection runs entirely on-device. No audio is sent to any cloud service during wake word detection.

**Requirements:**
- Model size: <5MB
- RAM usage: <20MB during idle
- CPU usage: <2% on modern hardware
- No GPU required
- Works offline (100% local)

### Power Consumption

Wake word detection is the most power-intensive always-on component.

**Targets:**
- Idle listening: <2% CPU
- Laptop battery impact: <5%/hour
- Desktop: Negligible

**Optimization strategies:**
- Audio buffer downsampling (16kHz → 8kHz for wake word)
- Periodic detection (every 100ms, not continuous)
- Adaptive sensitivity based on battery level
- Disable on battery saver mode (configurable)

### False Positives

False positives degrade trust. The system must be conservative.

**Targets:**
- False positive rate: <1% (1 in 100 non-wake utterances)
- False negative rate: <5% (wake word detected 95%+ of the time)

**Mitigation:**
- Two-stage detection: initial detection + confirmation
- Confidence threshold (configurable, default 0.7)
- User can train custom wake phrases for better accuracy
- False positive feedback loop: user reports improve model over time

### Sensitivity

Sensitivity is adjustable per wake phrase.

| Level | False Positive Rate | False Negative Rate | Use Case |
|-------|--------------------|--------------------|----------|
| Low | <0.5% | <15% | Noisy environments |
| Medium | <1% | <5% | Default, balanced |
| High | <3% | <2% | Quiet environments, maximum responsiveness |
| Custom | User-defined | User-defined | Advanced users |

### Privacy

Wake word detection is fully local. No audio leaves the device during detection.

**Privacy guarantees:**
- Wake word audio is processed in RAM, never written to disk
- No audio sent to cloud during detection
- No detection results sent to cloud
- User can view and delete detection logs
- Detection runs in a sandboxed process

### Multiple Wake Phrases

Users can configure multiple wake phrases.

**Defaults:**
- "Hey EVE" (primary)
- "EVE" (short, for quick commands)

**User-configurable:**
- Up to 5 custom phrases
- Each phrase has independent sensitivity setting
- Each phrase can trigger different behaviors (optional)
- Phrases stored locally, never uploaded

### Enable/Disable

Wake word can be toggled:

**User controls:**
- Global enable/disable (keyboard shortcut: Ctrl+Shift+V)
- Per-session enable/disable
- Scheduled disable (e.g., during meetings, sleep)
- Auto-disable when microphone is muted at OS level
- Visual indicator shows listening state (green = active, gray = disabled)

---

## Section 6 — Voice Activity Detection

### Speech Detection

VAD detects when the user starts speaking.

**Algorithm:**
- Energy-based detection (voice activity above noise floor)
- Spectral analysis (human voice frequency range: 80-3000Hz)
- Machine learning model (silero-vad or similar) for accuracy

**Targets:**
- Speech onset detection: <100ms
- Accuracy: >98% in quiet environments, >90% in moderate noise

### Silence Detection

VAD detects when the user stops speaking.

**Algorithm:**
- Energy drops below threshold for configurable duration
- Spectral analysis confirms silence
- Hysteresis to prevent flickering between speech/silence states

**Thresholds:**
- Short pause: 500ms (user thinking, continue listening)
- Medium pause: 2s (user finished turn, begin processing)
- Long pause: 5s (confirm "Still listening...")
- Conversation timeout: 10s (end conversation)

### Interruptions

VAD detects when the user speaks during EVE's speech.

**Algorithm:**
- Real-time audio analysis during TTS playback
- Voice energy above EVE's speech energy
- Spectral separation (user voice vs. TTS audio)

**Behavior:**
- User voice detected → EVE stops speaking within 500ms
- Partial EVE sentence discarded
- User's new input processed immediately
- No penalty for interruptions (natural conversation)

### Background Noise

The system must handle real-world environments.

**Environments supported:**
- Quiet room (<30dB): Full accuracy
- Moderate noise (30-50dB): Slightly reduced accuracy
- Noisy environment (50-70dB): Reduced accuracy, user can switch to push-to-talk
- Very noisy (>70dB): Push-to-talk recommended, wake word disabled

**Adaptive behavior:**
- Noise floor calibration on startup
- Dynamic threshold adjustment
- Noise profile stored per-location (optional)
- User can manually set noise profile

### Noise Suppression

Audio preprocessing removes background noise.

**Pipeline:**
1. Raw audio capture (16kHz, 16-bit)
2. Noise gate (below threshold → silence)
3. Spectral subtraction (remove consistent noise)
4. Beamforming (if multi-microphone available)
5. Clean audio → STT

**Targets:**
- Processing latency: <10ms
- CPU overhead: <1%
- Quality improvement: >3dB SNR

### Echo Cancellation

When EVE is speaking, the microphone must not capture EVE's own voice.

**Algorithm:**
- Adaptive filter modeling the acoustic path from speaker to microphone
- Reference signal from TTS output
- Real-time cancellation during speech playback

**Requirements:**
- Cancellation: >30dB echo suppression
- Latency: <5ms
- No distortion of user speech
- Works with any speaker/headphone configuration

### Hands-Free Mode

Full hands-free operation without any physical interaction.

**Mode activated by:**
- Settings toggle
- Voice command: "EVE, hands-free mode"
- Automatic when no keyboard/mouse activity for 5 minutes

**Behavior:**
- Wake word always active
- Push-to-talk disabled (prevents accidental activation)
- Conversation timeout extended (30 seconds)
- Confirmation spoken for all actions (no silent execution)
- Extra verbose responses (no assumed context)

---

## Section 7 — Streaming Voice

### Partial Transcription

STT provides partial results as audio is processed.

**Pipeline:**
1. Audio chunks (100ms each) sent to STT
2. STT returns partial transcription
3. Partial text displayed in overlay (real-time feedback)
4. Final transcription when silence detected

**Benefits:**
- User sees what EVE is hearing (confidence feedback)
- Early error detection (user can correct mid-sentence)
- Reduced perceived latency

### Partial Reasoning

For simple queries, EVE can begin reasoning before full transcription.

**Example:**
- User says "What's the wea—" → EVE starts checking weather API
- User completes "—ther?" → EVE already has data, responds faster

**Requirements:**
- Only for deterministic queries (weather, time, simple lookups)
- Non-deterministic queries wait for full transcription
- User can disable partial reasoning (opt-in)

### Streaming LLM

LLM responses are streamed token-by-token.

**Pipeline:**
1. Full user input sent to Smart Router
2. LLM begins generating tokens
3. Tokens streamed to TTS engine
4. TTS begins speaking as soon as enough tokens are buffered

**Buffer strategy:**
- First sentence buffered before TTS starts
- Subsequent sentences streamed (word-by-word handoff)
- Buffer size: 50-100ms of audio

### Streaming TTS

TTS generates audio as text is received.

**Pipeline:**
1. Text tokens received from LLM
2. TTS engine generates audio per-sentence
3. Audio chunks streamed to output device
4. Overlap: next sentence generated while current plays

**Targets:**
- First audio within 200ms of first token
- No gaps between sentences
- Smooth, natural prosody

### Word-Level Playback

EVE speaks word-by-word, not sentence-by-sentence.

**Benefits:**
- Lower perceived latency (user hears response sooner)
- Natural conversation rhythm
- Interruptible at word boundaries (clean stops)

**Implementation:**
- TTS generates word-level timing data
- Audio playback aligned to word boundaries
- Interruption happens at next word boundary (not mid-word)
- Visual overlay highlights current word (optional)

### Interruptible Speech

EVE can be interrupted at any point during speech.

**Behavior:**
- User voice detected → EVE stops within 500ms
- Stop happens at word boundary (not mid-word)
- Partial sentence discarded gracefully
- No "sorry" or acknowledgment (natural conversation)
- EVE remembers what it was saying (context preserved)

**Technical requirements:**
- Real-time audio monitoring during TTS playback
- Low-latency stop mechanism (<100ms)
- Clean audio cutoff (no clicks or pops)
- State preservation for interrupted sentences

### Low Latency Pipeline

The entire voice pipeline must be fast.

**Target latencies:**

| Stage | Target | Maximum |
|-------|--------|---------|
| Wake detection | <100ms | 200ms |
| Audio capture → STT | <50ms | 100ms |
| STT processing | <200ms | 500ms |
| LLM first token | <300ms | 1000ms |
| TTS first audio | <100ms | 200ms |
| **End-to-end** | **<1s** | **2s** |

**Optimization strategies:**
- Parallel processing (STT + context gathering)
- Streaming at every stage
- Local models for simple queries
- Provider selection optimized for latency
- Warm connections to frequently used providers
- Audio buffer pre-allocation

---

## Section 8 — Voice Personality

### EVE's Voice Character

EVE speaks like a knowledgeable, warm colleague — not a robot, not a servant, not a friend. Professional but approachable. Confident but not arrogant. Helpful but not subservient.

### Voice Characteristics

| Attribute | Value | Range |
|-----------|-------|-------|
| Pitch | Medium-high | 180-220Hz |
| Speed | 160-180 WPM | 120-220 WPM configurable |
| Tone | Warm, professional | Not cold, not overly casual |
| Articulation | Clear, natural | Not robotic, not slurred |
| Emotion | Subtle, context-appropriate | Not flat, not theatrical |

### Tone Profiles

| Context | Tone | Example |
|---------|------|---------|
| Answering a question | Confident, helpful | "The tests passed. 464 out of 464." |
| Reporting an error | Calm, constructive | "The provider timed out. I'll try another one." |
| Executing a command | Efficient, confirmatory | "Done. File saved." |
| Explaining something | Patient, clear | "Let me walk you through this." |
| Greeting | Warm, welcoming | "Good morning. What are we working on today?" |
| Uncertainty | Honest, exploratory | "I'm not sure about that. Let me look into it." |
| Confirmation | Clear, brief | "Got it." / "Understood." / "Sure." |
| Error recovery | Resilient, upbeat | "That didn't work, but I found another way." |

### Confirmation Phrases

EVE uses brief, natural confirmations:

| Action | Confirmation |
|--------|-------------|
| Task completed | "Done." / "Got it." / "All set." |
| Understanding | "Got it." / "Understood." / "Right." |
| Agreement | "Sure." / "Of course." / "Will do." |
| Starting task | "On it." / "Let me do that." / "Working on it." |
| Uncertainty | "Let me check." / "I'll look into that." |
| Apology (rare) | "Sorry about that." (only for genuine errors) |

### Greeting

EVE's greeting varies by time and context:

| Time | Greeting |
|------|----------|
| Morning (6-12) | "Good morning." / "Morning." |
| Afternoon (12-17) | "Good afternoon." / "Hey." |
| Evening (17-21) | "Good evening." |
| Night (21-6) | "Working late?" / "Hey." |
| After absence | "Welcome back." / "Hey, I'm here." |
| First time | "Hi, I'm EVE. What can I help you with?" |

### Error Responses

EVE handles errors gracefully:

| Error Type | Response Style | Example |
|------------|---------------|---------|
| Provider failure | Calm, proactive | "That provider is busy. Let me try another." |
| STT failure | Brief, helpful | "I didn't catch that. Could you say it again?" |
| Tool failure | Constructive | "That didn't work. Let me try a different approach." |
| Network failure | Honest | "I'm having trouble connecting. Let me try locally." |
| Unknown error | Transparent | "Something went wrong. I'll figure it out." |

EVE never says:
- "Error: [technical message]"
- "I'm sorry, I cannot..."
- "As an AI..."
- "I don't have the ability to..."
- "That's beyond my capabilities"

### Professional Mode

Default mode. Balanced between helpful and efficient.

- Responses: concise, accurate
- Confirmations: brief
- Errors: constructive
- Tone: warm but professional
- Verbosity: medium

### Companion Mode

More conversational, personality-forward.

- Responses: slightly longer, more context
- Confirmations: conversational
- Errors: empathetic
- Tone: friendly, relaxed
- Verbosity: high
- Small talk enabled

### Developer Mode

Optimized for coding workflows.

- Responses: technical, precise
- Confirmations: minimal ("done", "ok")
- Errors: detailed, actionable
- Tone: direct, efficient
- Verbosity: low
- Code always shown/spoken precisely
- File paths and line numbers included

---

## Section 9 — Overlay

### Floating Assistant

The overlay is a small, always-on-top window that shows EVE's state.

**Position:** Bottom-right corner (configurable)
**Size:** 48x48px (collapsed), 320x200px (expanded)
**Opacity:** 80% (configurable)
**Always on top:** Yes (except fullscreen apps)

### Collapsed Mode

Default state. Small circle showing EVE's status.

**Visual:**
- Circle (48x48px)
- Color indicates state:
  - Gray: IDLE
  - Blue pulse: LISTENING
  - Yellow spin: THINKING
  - Green wave: SPEAKING
- Subtle glow effect on state change
- Hover shows tooltip: "EVE — [state]"

**Interactions:**
- Click → Expand
- Right-click → Context menu (Settings, Disable, Quit)
- Drag → Reposition

### Expanded Mode

Full overlay with conversation display.

**Layout:**
```
+------------------------------------------+
| EVE                        [_] [X]       |
+------------------------------------------+
|                                          |
| [Partial transcription appears here]     |
|                                          |
| EVE: "The weather is 72°F and sunny."   |
|                                          |
| [Tool execution timeline]               |
|                                          |
+------------------------------------------+
| 🎤 Listening...            [Push-to-talk]|
+------------------------------------------+
```

**Components:**
- Header: EVE label, minimize, close
- Transcript area: User and EVE messages
- Tool timeline: Active tool executions
- Footer: Microphone state, push-to-talk button

### Listening Animation

When EVE is listening, the overlay shows a pulsing blue circle.

**Visual:**
- Concentric rings expanding outward
- Speed proportional to audio level
- Color: blue (#3B82F6)
- Ripple effect (CSS animation)

### Thinking Animation

When EVE is processing, the overlay shows a spinning yellow indicator.

**Visual:**
- Rotating dots (3 dots, circular motion)
- Color: yellow (#F59E0B)
- Speed: moderate (not frantic)
- Optional: brief status text ("Thinking..." / "Checking...")

### Speaking Animation

When EVE is speaking, the overlay shows a green waveform.

**Visual:**
- Audio waveform synced to TTS output
- Color: green (#10B981)
- Amplitude proportional to volume
- Smooth transitions between words

### Tool Execution Timeline

When tools are executing, the overlay shows a timeline.

**Visual:**
- Horizontal timeline bar
- Each tool as a colored segment
- Segment shows tool name and duration
- Green = success, red = failure, yellow = in progress
- Click segment for details

**Example:**
```
[EditFile ✓] [RunTests ✓] [GitCommit ▶]
  120ms       3.2s         in progress
```

### Minimal Mode

Ultra-compact overlay for unobtrusive use.

**Visual:**
- Single dot (12x12px)
- Color indicates state (same as collapsed)
- No text, no animations
- Click → Expand
- Position: corner of screen

### Accessibility

Overlay supports accessibility features:

- **High contrast mode:** Solid colors, no transparency
- **Reduced motion:** No animations, static indicators
- **Screen reader:** State announced via ARIA labels
- **Keyboard navigation:** Full keyboard control
- **Font scaling:** Text scales with OS font size
- **Color blind mode:** Patterns + colors (not color alone)

---

## Section 10 — Context Awareness

### Automatic Context

Voice commands automatically receive the full ExecutionContext. No manual context selection.

**Context provided to every voice request:**

| Context | Source | Use Case |
|---------|--------|----------|
| WindowContext | WindowProvider | "What app am I in?" |
| ClipboardContext | ClipboardProvider | "What did I just copy?" |
| WorkspaceContext | WorkspaceProvider | "What project is this?" |
| GitContext | GitProvider | "What branch am I on?" |
| BrowserContext | BrowserProvider | "What page is open?" |
| SelectionContext | SelectionProvider | "What text is selected?" |
| DesktopContext | DesktopProvider | "How many monitors?" |
| VoiceContext | VoiceProvider | "Is hands-free mode on?" |
| MemoryContext | MemoryProvider | "What were we talking about?" |
| ProviderHealthContext | ProviderHealthProvider | "Which provider is fastest?" |

### Context Resolving

Voice commands reference context implicitly.

**Examples:**
- "What is this?" → Resolves to SelectionContext or active window
- "Open that file" → Resolves to last-mentioned file in conversation
- "Run it" → Resolves to last-mentioned command
- "How does this work?" → Resolves to code in SelectionContext
- "Summarize this page" → Resolves to BrowserContext

### Context Carried Across Turns

Context persists across conversation turns.

**Example:**
```
User: "What's in main.py?"
EVE: "It's the entry point for the EVE application."
User: "What does it import?"
EVE: "It imports ContextEngine, SmartRouter, and ConversationPipeline."
User: "Show me the ContextEngine."
EVE: [Opens context/engine.py]
```

Each turn builds on previous context. The user never repeats themselves.

---

## Section 11 — AI Operations Center

### Voice Diagnostics Tab

A dedicated tab in the AI Operations Center for voice diagnostics.

**Layout:**
```
+------------------------------------------+
| VOICE DIAGNOSTICS                        |
+------------------------------------------+
| State: LISTENING                         |
| Wake Word: Active (OpenWakeWord)         |
| Confidence: 0.92                         |
+------------------------------------------+
| Microphone Level                         |
| [████████████░░░░░░░░] 65%              |
+------------------------------------------+
| Latencies                                |
| STT: 180ms (avg)                         |
| LLM: 320ms (first token)                |
| TTS: 95ms (first audio)                  |
| End-to-end: 1.2s (avg)                   |
+------------------------------------------+
| Streaming                                |
| Partial: "What's the weather in"         |
| Buffer: 45ms                             |
| Status: Capturing                        |
+------------------------------------------+
| Conversation Timeline                    |
| [00:00] User: "Hey EVE"                 |
| [00:01] EVE: [Listening]                |
| [00:03] User: "What's the weather?"     |
| [00:04] EVE: [Thinking]                 |
| [00:05] EVE: "It's 72°F and sunny."     |
| [00:06] User: "Thanks."                 |
| [00:07] EVE: "You're welcome."          |
+------------------------------------------+
```

### Live Microphone Level

Real-time microphone level visualization.

**Visual:**
- Horizontal bar showing current audio level
- Peak hold indicator (shows recent max)
- Color: green (normal), yellow (loud), red (clipping)
- Updates every 50ms

### STT Latency

Shows speech-to-text processing time.

**Metrics:**
- Current latency (ms)
- Average latency (last 10 requests)
- P95 latency (last 100 requests)
- Model in use (local/cloud)

### TTS Latency

Shows text-to-speech generation time.

**Metrics:**
- First audio latency (ms)
- Average sentence latency (ms)
- Engine in use (pyttsx3/cloud)
- Voice profile active

### Current State

Shows current voice session state.

**Information:**
- State: IDLE / LISTENING / THINKING / SPEAKING / FOLLOW-UP
- Duration in current state
- State transitions (last 10)
- Conversation turn count

### Wake Word Status

Shows wake word detection status.

**Information:**
- Engine: OpenWakeWord / Porcupine / Custom
- Status: Active / Disabled / Error
- Sensitivity: Low / Medium / High
- Last detection: timestamp
- Confidence: 0.0-1.0
- Custom phrases: list

### Streaming Status

Shows streaming pipeline status.

**Information:**
- STT streaming: Active / Inactive
- Partial transcription: current text
- LLM streaming: Active / Inactive
- TTS streaming: Active / Inactive
- Buffer size: ms
- Pipeline latency: ms

### Conversation Timeline

Chronological view of the current conversation.

**Information:**
- Timestamp for each event
- Speaker (User / EVE)
- Content (text or "[Thinking]" / "[Listening]")
- Latency for each turn
- Tools used (if any)

---

## Section 12 — Performance Targets

### Latency Targets

| Metric | Target | Maximum | Measurement |
|--------|--------|---------|-------------|
| Wake detection | <100ms | 200ms | Audio in → detection signal |
| STT processing | <200ms | 500ms | Audio in → text out |
| LLM first token | <300ms | 1000ms | Text in → first token |
| TTS first audio | <100ms | 200ms | Text in → audio out |
| End-to-end (simple) | <1s | 2s | Voice in → voice out |
| End-to-end (complex) | <3s | 5s | Voice in → voice out |
| Interruption response | <500ms | 1s | User interrupt → EVE stops |

### Resource Targets

| Resource | Target | Maximum | Condition |
|----------|--------|---------|-----------|
| CPU (idle) | <2% | 5% | Wake word listening only |
| CPU (active) | <15% | 30% | Full voice pipeline |
| RAM (idle) | <100MB | 150MB | Wake word model loaded |
| RAM (active) | <200MB | 300MB | Full pipeline |
| Disk (models) | <50MB | 100MB | Wake word + STT models |
| Battery (idle) | <3%/hr | 5%/hr | Laptop, continuous listening |
| Battery (active) | <8%/hr | 12%/hr | Laptop, active conversation |

### Quality Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| STT accuracy (quiet) | >97% | Word error rate |
| STT accuracy (noisy) | >90% | Word error rate |
| Wake word accuracy | >95% | True positive rate |
| False positive rate | <1% | Non-wake activations |
| TTS naturalness | >4.0/5 | MOS score |
| Interruption accuracy | >98% | Correct detection |

### Network Targets

| Metric | Target | Condition |
|--------|--------|-----------|
| Bandwidth (voice) | <50KB/s | Audio upload to cloud STT |
| Bandwidth (TTS) | <100KB/s | Cloud TTS download |
| Offline capability | Full wake + local STT | No network required |
| Fallback latency | <3s | Cloud to local provider switch |

---

## Section 13 — Privacy

### Always-On Listening

EVE listens for the wake word continuously. This requires careful privacy design.

**Privacy model:**
- Wake word detection: 100% local, no audio leaves device
- Audio after wake word: Processed locally (STT) or sent to cloud (if cloud STT selected)
- No audio recorded unless user explicitly enables recording
- No audio used for training
- No audio shared with third parties

### Offline Wake Word

Wake word detection works 100% offline.

**Guarantees:**
- No network connection required for wake word
- No data sent to cloud during detection
- Model stored locally, never updated automatically
- User controls model updates

### Microphone Permissions

EVE requests microphone access with clear explanation.

**Permission flow:**
1. First launch: "EVE needs microphone access for voice commands. Your audio is processed locally and never recorded without your permission."
2. OS permission dialog (system-managed)
3. Permission status shown in settings
4. User can revoke at any time
5. Graceful degradation if denied (chat-only mode)

### Local Processing

All voice processing can happen locally.

**Local pipeline:**
- Wake word: Local model
- STT: Local model (Whisper small/medium, Vosk, etc.)
- LLM: Local model (Ollama) or cloud (via Smart Router)
- TTS: Local engine (pyttsx3)

**No cloud required for full voice functionality.**

### Cloud Processing

Cloud processing is optional, for higher quality.

**Cloud pipeline:**
- Wake word: Always local (privacy requirement)
- STT: Cloud API (OpenAI Whisper API, Google Speech, etc.)
- LLM: Cloud via Smart Router
- TTS: Cloud API (ElevenLabs, Azure, etc.)

**User controls:**
- Enable/disable cloud STT
- Enable/disable cloud TTS
- Per-provider cloud settings
- Data retention policies per provider

### Recording Policy

EVE does not record audio by default.

**Rules:**
- No audio saved to disk (unless user enables)
- No conversation audio retained after processing
- Transcription text stored in session memory (ephemeral)
- User can enable recording for debugging (opt-in)
- Recording stored locally, never uploaded
- User can delete all recordings at any time

### User Controls

Complete user control over voice privacy.

**Settings:**
- Wake word enable/disable
- Microphone access enable/disable
- Cloud STT enable/disable
- Cloud TTS enable/disable
- Recording enable/disable
- Conversation history retention (session/project/global/none)
- Auto-delete recordings after N days
- Privacy mode (reduced functionality, maximum privacy)
- Audit log of all voice interactions

---

## Section 14 — Failure Handling

### Microphone Unavailable

**Scenario:** Microphone not detected, driver failure, or permission denied.

**Recovery:**
1. Detect microphone availability on startup
2. If unavailable: fall back to chat-only mode
3. Show notification: "Microphone not available. Voice commands disabled."
4. Provide troubleshooting: "Check microphone connection and permissions."
5. Auto-retry microphone detection every 30 seconds
6. Resume voice mode when microphone becomes available

### Wake Word Failure

**Scenario:** Wake word not detecting or too many false positives.

**Recovery:**
1. Log failure to error intelligence
2. If false positives: reduce sensitivity
3. If not detecting: prompt user to retrain wake phrase
4. Fallback: push-to-talk mode
5. User can disable wake word and use push-to-talk only
6. Provide diagnostic: "Wake word accuracy reduced. Try retraining."

### STT Failure

**Scenario:** Speech-to-text fails to transcribe.

**Recovery:**
1. Retry transcription (up to 2 attempts)
2. If cloud STT fails: switch to local STT
3. If local STT fails: show partial transcription (if available)
4. If all STT fails: "I didn't catch that. Could you say it again?"
5. Log failure for diagnostics
6. If persistent: suggest push-to-talk or chat mode

### TTS Failure

**Scenario:** Text-to-speech fails to generate audio.

**Recovery:**
1. Retry TTS (up to 2 attempts)
2. If cloud TTS fails: switch to local TTS
3. If local TTS fails: display response as text in overlay
4. "I can't speak right now, but here's my response: [text]"
5. Log failure for diagnostics
6. If persistent: switch to text-only mode

### Provider Timeout

**Scenario:** LLM provider times out during voice request.

**Recovery:**
1. Smart Router automatically retries with another provider
2. If all providers timeout: "I'm having trouble connecting. Let me try locally."
3. Fallback to local model (Ollama)
4. If no local model: "I can't reach any providers right now. Try again in a moment."
5. Log failure for error intelligence
6. Update provider health scores

### Network Failure

**Scenario:** Internet connection lost during voice session.

**Recovery:**
1. Detect network loss
2. Switch to fully local pipeline (wake word + local STT + local LLM + local TTS)
3. Inform user: "Network lost. Using local processing."
4. Maintain voice functionality (reduced quality)
5. Auto-reconnect when network restored
6. Resume full pipeline on reconnect

### Streaming Interruption

**Scenario:** Streaming voice pipeline interrupted (buffer overflow, network hiccup).

**Recovery:**
1. Detect stream interruption
2. Pause playback
3. Rebuffer (if recoverable)
4. Resume from last successful position
5. If unrecoverable: restart from beginning of current sentence
6. Inform user if interruption was noticeable

### Recovery Behaviour

All failures are captured by AI Error Intelligence.

**Error flow:**
1. Failure detected
2. `_capture_error()` called with error details
3. Error classified (category, severity)
4. Recovery strategy selected
5. Recovery attempted
6. Result recorded in error timeline
7. User informed (if necessary)
8. Provider health updated
9. Dashboard updated

**User-facing recovery:**
- Brief, constructive messages
- Never technical jargon
- Always offer alternative ("Try again" / "Use another provider" / "Switch to chat")
- Never blame the user

---

## Section 15 — Accessibility

### Keyboard Fallback

Full voice functionality available via keyboard.

**Keyboard shortcuts:**
- Ctrl+Space: Push-to-talk (hold to speak)
- Ctrl+Shift+V: Toggle voice mode
- Ctrl+Shift+M: Toggle microphone
- Escape: Cancel current operation
- Tab: Navigate overlay elements
- Enter: Select/confirm

**Chat mode:** Always available as fallback. User can switch between voice and chat at any time.

### Screen Readers

Overlay is screen-reader accessible.

**ARIA labels:**
- State announced: "EVE is listening" / "EVE is thinking" / "EVE is speaking"
- Transcription area: aria-live="polite" (announces new messages)
- Tool timeline: aria-label for each tool
- Buttons: descriptive labels

**Compatibility:** NVDA, JAWS, VoiceOver, Narrator.

### Visual Indicators

All audio events have visual counterparts.

**Indicators:**
- Listening: Blue pulsing circle
- Thinking: Yellow spinning indicator
- Speaking: Green waveform
- Error: Red flash
- Tool execution: Timeline bar
- State changes: Subtle transition animation

**Users who are deaf or hard-of-hearing can fully use EVE via visual indicators + chat.**

### Captions

Spoken responses are captioned in the overlay.

**Caption features:**
- Real-time captions during speech
- Word-by-word highlighting
- Speaker labels (User / EVE)
- Timestamp for each caption
- Exportable as text
- Font size adjustable

### Speech Rate

EVE's speaking rate is adjustable.

**Range:** 100-250 WPM (words per minute)
**Default:** 170 WPM
**Adjustment:** Settings menu or voice command ("Speak slower" / "Speak faster")

### Voice Selection

Multiple voice profiles available.

**Options:**
- Default (EVE voice)
- Male voice
- Female voice
- Neutral voice
- Custom voice (future: voice cloning)

**Each profile has independent pitch, speed, and tone settings.**

### Hearing-Impaired Mode

Optimized for users who are deaf or hard-of-hearing.

**Features:**
- All responses displayed as text (overlay or chat)
- Visual indicators for all audio events
- Vibration feedback on state changes (if supported)
- Captions always visible (not togglable)
- No audio required for full functionality
- Emergency alerts via system notification (not audio)

---

## Section 16 — Roadmap

### Sprint D1: Wake Word Foundation

**Duration:** 2 weeks
**Objectives:**
- Implement wake word engine abstraction
- Integrate OpenWakeWord as default engine
- Create WakeWordProvider for Context Engine
- Implement configurable wake phrases
- Add wake word settings to AioSettings

**Deliverables:**
- `aios/voice/wake_word/` package (engine abstraction + OpenWakeWord impl)
- `WakeWordProvider` (Context Engine integration)
- Settings UI for wake word configuration
- Tests: wake word detection, false positive rate, sensitivity

**Acceptance Criteria:**
- Wake word detects "Hey EVE" with >95% accuracy
- False positive rate <1%
- CPU usage <2% during idle listening
- Works offline (no network required)
- Settings persist across restarts

**Testing Strategy:**
- Unit tests for engine abstraction
- Integration tests with recorded audio samples
- Performance benchmarks (CPU, RAM, latency)
- Manual testing with various microphones

---

### Sprint D2: Continuous Conversation

**Duration:** 2 weeks
**Objectives:**
- Implement conversation lifecycle state machine
- Add automatic re-listening after EVE response
- Implement conversation timeout
- Add follow-up context resolution
- Multiple conversation support

**Deliverables:**
- `VoiceStateMachine` (IDLE → LISTENING → THINKING → SPEAKING → FOLLOW-UP)
- Conversation timeout configuration
- Follow-up pronoun resolution
- Multi-conversation context switching
- Tests: lifecycle transitions, timeout, follow-ups

**Acceptance Criteria:**
- Conversation continues without re-wake
- Timeout works correctly (10s default)
- Follow-up questions resolve context
- Up to 5 concurrent conversations
- Clean state transitions

**Testing Strategy:**
- Unit tests for state machine
- Integration tests for conversation flow
- Manual testing with real conversations
- Edge case testing (interruptions, timeouts, context switches)

---

### Sprint D3: Voice Activity Detection

**Duration:** 2 weeks
**Objectives:**
- Implement VAD engine (speech/silence detection)
- Add noise suppression
- Add echo cancellation
- Background noise adaptation
- Push-to-talk mode

**Deliverables:**
- `aios/voice/vad/` package
- Noise suppression pipeline
- Echo cancellation (reference from TTS output)
- Push-to-talk keyboard shortcut
- Settings for VAD sensitivity

**Acceptance Criteria:**
- Speech onset detection <100ms
- Silence detection accurate (no premature cutoff)
- Echo cancellation >30dB suppression
- Push-to-talk works reliably
- Adapts to background noise

**Testing Strategy:**
- Unit tests for VAD algorithm
- Integration tests with noise samples
- Performance benchmarks
- Manual testing in various environments

---

### Sprint D4: Interruptions

**Duration:** 1 week
**Objectives:**
- Implement interruption detection during TTS playback
- Add clean stop mechanism
- Implement word-boundary interruption
- State preservation on interruption
- Interruption UX (no apology, natural flow)

**Deliverables:**
- Interruption detection during TTS
- Clean audio cutoff mechanism
- Word-boundary stop logic
- Interrupted context preservation
- Tests: interruption detection, cleanup, state preservation

**Acceptance Criteria:**
- EVE stops within 500ms of user interrupt
- Clean stop (no audio artifacts)
- Stops at word boundary (not mid-word)
- Interrupted context preserved for follow-up
- No "sorry" or acknowledgment

**Testing Strategy:**
- Unit tests for interruption detection
- Integration tests with TTS playback
- Manual testing with real interruptions
- Edge case testing (interrupt during tool execution)

---

### Sprint D5: Streaming Voice

**Duration:** 2 weeks
**Objectives:**
- Implement streaming STT (partial transcription)
- Implement streaming LLM → TTS pipeline
- Add word-level TTS playback
- Low-latency pipeline optimization
- Streaming status in overlay

**Deliverables:**
- Streaming STT integration
- Streaming LLM → TTS pipeline
- Word-level audio playback
- Streaming status display
- Tests: pipeline latency, word-level timing, streaming quality

**Acceptance Criteria:**
- Partial transcription displayed in real-time
- First audio within 200ms of first token
- Word-level playback (no sentence gaps)
- End-to-end latency <2s for simple queries
- Streaming status shown in overlay

**Testing Strategy:**
- Latency benchmarks at each pipeline stage
- Integration tests with streaming providers
- Manual testing with real conversations
- Quality assessment (naturalness, timing)

---

### Sprint D6: Desktop Overlay

**Duration:** 2 weeks
**Objectives:**
- Implement floating overlay window
- Add collapsed/expanded/minimal modes
- Implement state animations (listening, thinking, speaking)
- Add tool execution timeline
- Overlay repositioning and settings

**Deliverables:**
- Tauri overlay window
- Collapsed mode (48x48px circle)
- Expanded mode (conversation display)
- Minimal mode (12x12px dot)
- State animations (CSS)
- Tool execution timeline
- Overlay settings (position, opacity, size)

**Acceptance Criteria:**
- Overlay displays correctly on all screen sizes
- Animations smooth (60fps)
- Always on top (except fullscreen)
- Repositionable by drag
- Settings persist across restarts
- Accessibility (screen reader, keyboard nav)

**Testing Strategy:**
- Visual regression tests
- Performance tests (animation frame rate)
- Multi-monitor testing
- Accessibility testing (screen reader, keyboard)
- Manual UX testing

---

### Sprint D7: Voice Diagnostics

**Duration:** 1 week
**Objectives:**
- Add Voice Diagnostics tab to AI Operations Center
- Implement live microphone level
- Add latency metrics (STT, LLM, TTS)
- Conversation timeline display
- Wake word status display

**Deliverables:**
- Voice Diagnostics tab in AIOperationsCenter
- Live microphone level visualization
- Latency metrics dashboard
- Conversation timeline view
- Wake word status display

**Acceptance Criteria:**
- Microphone level updates in real-time
- Latency metrics accurate
- Conversation timeline shows all events
- Wake word status correct
- No performance impact on voice pipeline

**Testing Strategy:**
- Unit tests for metrics collection
- Integration tests for diagnostics display
- Performance impact verification
- Manual testing with voice sessions

---

### Sprint D8: Performance Optimization

**Duration:** 2 weeks
**Objectives:**
- Optimize wake word detection (CPU, memory)
- Optimize STT pipeline (latency, accuracy)
- Optimize TTS pipeline (latency, naturalness)
- Optimize overlay (rendering, animations)
- Battery impact optimization
- Memory leak detection and fixes

**Deliverables:**
- Performance benchmarks document
- CPU/memory profiling results
- Battery impact measurements
- Optimization patches
- Memory leak fixes
- Final performance report

**Acceptance Criteria:**
- All latency targets met (see Section 12)
- All resource targets met (see Section 12)
- Battery impact <5%/hour idle
- No memory leaks detected
- CPU idle <2%
- RAM idle <150MB

**Testing Strategy:**
- Performance benchmarks (before/after comparison)
- Stress testing (extended sessions)
- Memory profiling (leak detection)
- Battery drain testing (laptop)
- Cross-hardware testing (different CPUs, RAM)

---

## End of Phase D VoiceOS+ PRD

This document is the complete product specification for VoiceOS+.

After approval, Phase D implementation will begin exactly according to this PRD.

**Frozen Kernel:** Phase C (v2.0-alpha)
**Tests:** 464/464 passing
**Next:** Tag v2.0-alpha, then begin Sprint D1.
