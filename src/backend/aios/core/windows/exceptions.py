"""Typed exceptions for the Windows Adapter layer."""


class WindowsAdapterError(Exception):
    code = "WINDOWS_ADAPTER_ERROR"


class FileOperationError(WindowsAdapterError):
    code = "FILE_OPERATION_ERROR"


class FileNotFoundError_(FileOperationError):
    code = "FILE_NOT_FOUND"


class PathTraversalError(FileOperationError):
    code = "PATH_TRAVERSAL"


class PermissionDeniedError(WindowsAdapterError):
    code = "PERMISSION_DENIED"


class ClipboardError(WindowsAdapterError):
    code = "CLIPBOARD_ERROR"


class ProcessError(WindowsAdapterError):
    code = "PROCESS_ERROR"


class ProcessNotFoundError(ProcessError):
    code = "PROCESS_NOT_FOUND"


class ProcessTerminationError(ProcessError):
    code = "PROCESS_TERMINATION_FAILED"


class ActiveWindowError(WindowsAdapterError):
    code = "ACTIVE_WINDOW_ERROR"


class MonitorError(WindowsAdapterError):
    code = "MONITOR_ERROR"


class UIAutomationError(WindowsAdapterError):
    code = "UI_AUTOMATION_ERROR"


class SystemInfoError(WindowsAdapterError):
    code = "SYSTEM_INFO_ERROR"


class ValidationError(WindowsAdapterError):
    code = "VALIDATION_ERROR"
