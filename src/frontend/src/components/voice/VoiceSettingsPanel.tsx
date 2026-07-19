import { useState, useEffect } from "react";
import { voiceService, VoiceConfig } from "../../services/voice";

interface VoiceSettingsPanelProps {
  onClose?: () => void;
}

export default function VoiceSettingsPanel({ onClose }: VoiceSettingsPanelProps) {
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [inputDevices, setInputDevices] = useState<{ id: string; name: string }[]>([]);
  const [outputDevices, setOutputDevices] = useState<{ id: string; name: string }[]>([]);
  const [voices, setVoices] = useState<{ id: string; name: string }[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
    loadDevices();
    loadVoices();
  }, []);

  const loadConfig = async () => {
    try {
      const cfg = await voiceService.fetchConfig();
      setConfig(cfg);
    } catch (e) {
      console.error("load config error", e);
    }
  };

  const loadDevices = async () => {
    try {
      const [inputs, outputs] = await Promise.all([
        voiceService.fetchInputDevices(),
        voiceService.fetchOutputDevices(),
      ]);
      setInputDevices(inputs);
      setOutputDevices(outputs);
    } catch (e) {
      console.error("load devices error", e);
    }
  };

  const loadVoices = async () => {
    try {
      const v = await voiceService.fetchVoices();
      setVoices(v);
    } catch (e) {
      console.error("load voices error", e);
    }
  };

  const update = (key: keyof VoiceConfig, value: any) => {
    if (!config) return;
    setConfig({ ...config, [key]: value });
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await voiceService.updateConfig(config);
      onClose?.();
    } catch (e) {
      console.error("save config error", e);
    } finally {
      setSaving(false);
    }
  };

  if (!config) {
    return <div className="settings-loading">Loading voice settings...</div>;
  }

  return (
    <div className="voice-settings">
      <div className="setting-group">
        <label>STT Provider</label>
        <select value={config.stt_provider} onChange={(e) => update("stt_provider", e.target.value)}>
          <option value="whisper">Whisper (Local)</option>
          <option value="google">Google Speech</option>
          <option value="sphinx">Sphinx (Offline)</option>
          <option value="azure">Azure Speech</option>
        </select>
      </div>

      <div className="setting-group">
        <label>TTS Provider</label>
        <select value={config.tts_provider} onChange={(e) => update("tts_provider", e.target.value)}>
          <option value="pyttsx3">pyttsx3 (Offline)</option>
          <option value="edge">Edge TTS</option>
          <option value="azure">Azure TTS</option>
        </select>
      </div>

      <div className="setting-group">
        <label>Input Device (Microphone)</label>
        <select
          value={config.input_device || ""}
          onChange={(e) => update("input_device", e.target.value || null)}
        >
          <option value="">Default</option>
          {inputDevices.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      <div className="setting-group">
        <label>Output Device</label>
        <select
          value={config.output_device || ""}
          onChange={(e) => update("output_device", e.target.value || null)}
        >
          <option value="">Default</option>
          {outputDevices.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </div>

      <div className="setting-group">
        <label>Language</label>
        <select value={config.language} onChange={(e) => update("language", e.target.value)}>
          <option value="en-US">English (US)</option>
          <option value="en-GB">English (UK)</option>
          <option value="es-ES">Spanish</option>
          <option value="fr-FR">French</option>
          <option value="de-DE">German</option>
          <option value="ja-JP">Japanese</option>
          <option value="zh-CN">Chinese (Simplified)</option>
          <option value="hi-IN">Hindi</option>
          <option value="pt-BR">Portuguese (Brazil)</option>
          <option value="ar-SA">Arabic</option>
        </select>
      </div>

      <div className="setting-group">
        <label>Voice</label>
        <select value={config.voice_id} onChange={(e) => update("voice_id", e.target.value)}>
          <option value="">Default</option>
          {voices.map((v) => (
            <option key={v.id} value={v.id}>{v.name}</option>
          ))}
        </select>
      </div>

      <div className="setting-group">
        <label>Speaking Rate: {config.speaking_rate.toFixed(1)}x</label>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.1"
          value={config.speaking_rate}
          onChange={(e) => update("speaking_rate", parseFloat(e.target.value))}
        />
      </div>

      <div className="setting-group">
        <label>Pitch: {config.pitch.toFixed(1)}</label>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.1"
          value={config.pitch}
          onChange={(e) => update("pitch", parseFloat(e.target.value))}
        />
      </div>

      <div className="setting-group">
        <label>Push-to-Talk Key</label>
        <input
          type="text"
          value={config.push_to_talk_key}
          onChange={(e) => update("push_to_talk_key", e.target.value)}
          maxLength={1}
          style={{ textTransform: "uppercase", width: 60, textAlign: "center" }}
        />
      </div>

      <div className="setting-group">
        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={config.wake_word_enabled}
            onChange={(e) => update("wake_word_enabled", e.target.checked)}
          />
          Wake Word Detection
        </label>
      </div>

      {config.wake_word_enabled && (
        <div className="setting-group">
          <label>Wake Word</label>
          <input
            type="text"
            value={config.wake_word}
            onChange={(e) => update("wake_word", e.target.value)}
          />
        </div>
      )}

      <div className="setting-group">
        <label className="setting-toggle">
          <input
            type="checkbox"
            checked={config.continuous_listening}
            onChange={(e) => update("continuous_listening", e.target.checked)}
          />
          Continuous Listening
        </label>
      </div>

      <div className="settings-footer">
        {onClose && (
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
        )}
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
