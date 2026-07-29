export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  tokens_used: number;
  attachments: any[];
  tool_calls?: any[];
  metadata: Record<string, any>;
}

export interface ConversationState {
  activeId: string | null;
  messages: Message[];
  streaming: boolean;
  streamingContent: string;
  statusMessage: string;
  loading: boolean;
  error: string | null;
}

export interface ConversationActions {
  sendMessage: (content: string) => Promise<void>;
  cancelStream: () => void;
  retryLast: () => void;
  createConversation: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => void;
}
