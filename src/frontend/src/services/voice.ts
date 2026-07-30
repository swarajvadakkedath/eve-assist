import { API_BASE } from "./api";

const API_BASE_VOICE = `${API_BASE}/voice`;
const API_BASE_WS = API_BASE.startsWith("http")
  ? API_BASE.replace(/^http/, "ws")
  : `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}${API_BASE}`;

type VoiceEventHandler = (event: { type: string; data: any }) => void;

interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
  state: string;
  sessionId: string;
  conversationId: string;
  currentTranscript: string;
  audioLevel: number;
}

interface VoiceConfig {
  stt_provider: string;
  tts_provider: string;
  input_device: string | null;
  output_device: string | null;
  language: string;
  voice_id: string;
  speaking_rate: number;
  pitch: number;
  push_to_talk_key: string;
  wake_word_enabled: boolean;
  wake_word: string;
  continuous_listening: boolean;
}

class VoiceService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Set<VoiceEventHandler>> = new Map();
  private _state: VoiceState = {
    isListening: false,
    isSpeaking: false,
    state: "idle",
    sessionId: "",
    conversationId: "",
    currentTranscript: "",
    audioLevel: 0,
  };
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  get state() {
    return this._state;
  }

  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${API_BASE_WS}/voice/ws`;

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
          }
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            this.handleMessage(msg);
          } catch (e) {
            console.error("voice: parse error", e);
          }
        };

        this.ws.onclose = () => {
          this.ws = null;
          this.emit("voice:disconnected", {});
          this.scheduleReconnect();
        };

        this.ws.onerror = (err) => {
          reject(err);
        };
      } catch (e) {
        reject(e);
      }
    });
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(() => {});
    }, 3000);
  }

  private handleMessage(msg: any): void {
    switch (msg.type) {
      case "voice:listening:start":
        this._state = { ...this._state, isListening: true, state: "listening" };
        break;
      case "voice:listening:stop":
        this._state = { ...this._state, isListening: false, state: "idle" };
        break;
      case "voice:transcript:partial":
        this._state = {
          ...this._state,
          currentTranscript: msg.data?.text || "",
        };
        break;
      case "voice:transcript:final":
        this._state = {
          ...this._state,
          currentTranscript: msg.data?.text || "",
        };
        break;
      case "voice:speaking:start":
        this._state = { ...this._state, isSpeaking: true, state: "speaking" };
        break;
      case "voice:speaking:stop":
        this._state = { ...this._state, isSpeaking: false, state: "idle" };
        break;
      case "voice:state:change":
        this._state = {
          ...this._state,
          state: msg.data?.state || this._state.state,
        };
        break;
      case "voice:audio:level":
        this._state = {
          ...this._state,
          audioLevel: msg.data?.level || 0,
        };
        break;
      case "state":
        if (msg.data) {
          this._state = {
            ...this._state,
            isListening: msg.data.is_listening,
            isSpeaking: msg.data.is_speaking,
            state: msg.data.state,
            sessionId: msg.data.session_id || this._state.sessionId,
            currentTranscript: msg.data.current_transcript || this._state.currentTranscript,
          };
        }
        break;
      case "listening:started":
        this._state = { ...this._state, isListening: true, state: "listening" };
        break;
      case "listening:stopped":
        this._state = {
          ...this._state,
          isListening: false,
          state: "idle",
          currentTranscript: msg.transcript || "",
        };
        break;
      case "speaking:started":
        this._state = { ...this._state, isSpeaking: true, state: "speaking" };
        break;
      case "speaking:stopped":
        this._state = { ...this._state, isSpeaking: false, state: "idle" };
        break;
      case "barge_in:done":
        this._state = { ...this._state, isSpeaking: false, state: "idle" };
        break;
    }
    this.emit(msg.type, msg.data || msg);
  }

  on(event: string, handler: VoiceEventHandler): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
    return () => {
      this.listeners.get(event)?.delete(handler);
    };
  }

  private emit(event: string, data: any): void {
    this.listeners.get(event)?.forEach((h) => h({ type: event, data }));
    this.listeners.get("*")?.forEach((h) => h({ type: event, data }));
  }

  async send(action: string, payload: Record<string, unknown> = {}): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      await this.connect();
    }
    this.ws?.send(JSON.stringify({ action, ...payload }));
  }

  startListening(language?: string): Promise<void> {
    return this.send("start_listening", { language });
  }

  stopListening(): Promise<void> {
    return this.send("stop_listening");
  }

  speak(text: string): Promise<void> {
    return this.send("speak", { text });
  }

  stopSpeaking(): Promise<void> {
    return this.send("stop_speaking");
  }

  bargeIn(): Promise<void> {
    return this.send("barge_in");
  }

  sendText(text: string): Promise<void> {
    return this.send("send_text", { text });
  }

  getState(): Promise<void> {
    return this.send("get_state");
  }

  async fetchState(): Promise<VoiceState> {
    const res = await fetch(`${API_BASE_VOICE}/state`);
    const data = await res.json();
    this._state = {
      isListening: data.is_listening,
      isSpeaking: data.is_speaking,
      state: data.state,
      sessionId: data.session_id,
      conversationId: data.conversation_id || "",
      currentTranscript: data.current_transcript || "",
      audioLevel: data.audio_level || 0,
    };
    return this._state;
  }

  async startSession(conversationId?: string): Promise<{ session_id: string; conversation_id: string }> {
    const res = await fetch(`${API_BASE_VOICE}/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: conversationId }),
    });
    const data = await res.json();
    this._state = {
      ...this._state,
      sessionId: data.session_id,
      conversationId: data.conversation_id,
    };
    return data;
  }

  async stopSession(): Promise<void> {
    await fetch(`${API_BASE_VOICE}/session/stop`, { method: "POST" });
    this._state = {
      isListening: false,
      isSpeaking: false,
      state: "idle",
      sessionId: "",
      conversationId: "",
      currentTranscript: "",
      audioLevel: 0,
    };
  }

  async fetchConfig(): Promise<VoiceConfig> {
    const res = await fetch(`${API_BASE_VOICE}/config`);
    return res.json();
  }

  async updateConfig(config: Partial<VoiceConfig>): Promise<void> {
    await fetch(`${API_BASE_VOICE}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config }),
    });
  }

  async fetchInputDevices(): Promise<{ id: string; name: string; is_default: boolean }[]> {
    const res = await fetch(`${API_BASE_VOICE}/devices/input`);
    const data = await res.json();
    return data.devices || [];
  }

  async fetchOutputDevices(): Promise<{ id: string; name: string; is_default: boolean }[]> {
    const res = await fetch(`${API_BASE_VOICE}/devices/output`);
    const data = await res.json();
    return data.devices || [];
  }

  async fetchVoices(): Promise<{ id: string; name: string; languages: string[]; gender: string }[]> {
    const res = await fetch(`${API_BASE_VOICE}/voices`);
    const data = await res.json();
    return data.voices || [];
  }
}

export const voiceService = new VoiceService();
export type { VoiceState, VoiceConfig, VoiceEventHandler };
