export interface MessageAvatarProps {
  role: "user" | "assistant" | "system";
}

const avatarConfig: Record<string, { label: string; className: string }> = {
  user: { label: "U", className: "pr-msg-avatar-user" },
  assistant: { label: "E", className: "pr-msg-avatar-assistant" },
  system: { label: "S", className: "pr-msg-avatar-system" },
};

function MessageAvatar({ role }: MessageAvatarProps) {
  const config = avatarConfig[role] || avatarConfig.system;
  return (
    <div className={`pr-msg-avatar ${config.className}`} aria-hidden="true">
      {config.label}
    </div>
  );
}

export default MessageAvatar;
