export type CommandCategory =
  | "app"
  | "workspace"
  | "tool"
  | "plugin"
  | "conversation"
  | "session"
  | "memory"
  | "browser"
  | "voice"
  | "vision"
  | "developer"
  | "file"
  | "nlp"
  | "recent";

export type CommandResultType =
  | "open-workspace"
  | "open-conversation"
  | "open-session"
  | "execute-tool"
  | "open-panel"
  | "nlp-query"
  | "open-url"
  | "run-command"
  | "run-plugin"
  | "search-query";

export interface CommandItem {
  id: string;
  name: string;
  description: string;
  category: CommandCategory;
  resultType: CommandResultType;
  icon?: string;
  shortcut?: string;
  keywords?: string[];
  payload?: unknown;
  action: () => void;
  highlight?: boolean;
}

export interface CommandProvider {
  id: string;
  name: string;
  commands: CommandItem[];
  search(query: string): Promise<CommandItem[]>;
  refresh?(): Promise<void>;
}

export interface CommandHistoryEntry {
  commandId: string;
  executedAt: string;
  pinned?: boolean;
}

export interface CommandGroup {
  label: string;
  commands: CommandItem[];
}

export interface CommandStoreState {
  query: string;
  results: CommandItem[];
  groups: CommandGroup[];
  selectedIndex: number;
  loading: boolean;
  error: string | null;
  recentCommands: CommandHistoryEntry[];
  pinnedCommands: string[];
}

export interface CommandPreviewData {
  item: CommandItem;
  description: string;
  category: CommandCategory;
  shortcut?: string;
  estimatedAction: string;
}

export interface NaturalLanguageIntent {
  text: string;
  intent: string;
  confidence: number;
  suggestedCommand?: CommandItem;
  resultType: CommandResultType;
  payload?: unknown;
}

export interface CommandCenterProps {
  workspaces: { id: string; label: string; icon?: string }[];
  onClose: () => void;
  onNavigate: (action: string, payload?: string) => void;
  onSwitchWorkspace?: (workspaceId: string) => void;
  activeWorkspaceId?: string;
  defaultQuery?: string;
}

export interface CommandInputProps {
  value: string;
  onChange: (value: string) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  placeholder?: string;
  inputRef: React.RefObject<HTMLInputElement>;
}

export interface CommandResultsProps {
  groups: CommandGroup[];
  selectedIndex: number;
  onSelect: (item: CommandItem) => void;
  onHover: (index: number) => void;
  loading: boolean;
  error: string | null;
  query: string;
}

export interface CommandCategoryProps {
  label: string;
  count?: number;
}

export interface CommandItemRowProps {
  item: CommandItem;
  selected: boolean;
  onSelect: () => void;
  onHover: () => void;
}

export interface CommandPreviewProps {
  data: CommandPreviewData | null;
}

export interface CommandHistoryProps {
  entries: CommandHistoryEntry[];
  pinnedIds: string[];
  onSelect: (item: CommandItem) => void;
  onTogglePin: (commandId: string) => void;
  onClear: () => void;
  allCommands: Map<string, CommandItem>;
}

export interface CommandSuggestionsProps {
  suggestions: CommandItem[];
  onSelect: (item: CommandItem) => void;
}

export interface CommandFooterProps {
  totalResults: number;
  selectedIndex: number;
  hasQuery: boolean;
}

export interface CommandShortcutProps {
  shortcut: string;
}

export interface CommandEmptyStateProps {
  query: string;
  hasSuggestions?: boolean;
}

export interface CommandLoadingStateProps {
  message?: string;
}

export interface CommandErrorStateProps {
  error: string;
  onRetry?: () => void;
}

export interface NaturalLanguageResultProps {
  intent: NaturalLanguageIntent;
  onExecute: (item: CommandItem) => void;
}
