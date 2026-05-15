"""Domain-specific exceptions for the PEA system."""


class PEAException(Exception):
    """Base exception for all PEA errors."""

    def __init__(self, message: str, code: str = "UNKNOWN", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class LLMProviderError(PEAException):
    """Raised when LLM provider call fails."""

    def __init__(self, provider: str, message: str, details: dict | None = None):
        super().__init__(
            message=f"LLM 提供商 '{provider}' 错误: {message}",
            code="LLM_PROVIDER_ERROR",
            details={"provider": provider, **(details or {})},
        )


class RetrievalError(PEAException):
    """Raised when RAG retrieval fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message=message, code="RETRIEVAL_ERROR", details=details)


class DocumentProcessingError(PEAException):
    """Raised when document parsing or chunking fails."""

    def __init__(self, file_path: str, message: str, details: dict | None = None):
        super().__init__(
            message=f"处理文档 '{file_path}' 失败: {message}",
            code="DOCUMENT_PROCESSING_ERROR",
            details={"file_path": file_path, **(details or {})},
        )


class WorkflowStateError(PEAException):
    """Raised when workflow state transition is invalid."""

    def __init__(self, current_state: str, target_state: str, message: str = ""):
        super().__init__(
            message=f"无效的状态转换: {current_state} -> {target_state}. {message}",
            code="WORKFLOW_STATE_ERROR",
            details={"current_state": current_state, "target_state": target_state},
        )


class CitationVerificationError(PEAException):
    """Raised when citation cannot be verified against source."""

    def __init__(self, citation_id: str, message: str):
        super().__init__(
            message=f"引用 '{citation_id}' 验证失败: {message}",
            code="CITATION_VERIFICATION_ERROR",
            details={"citation_id": citation_id},
        )


class HumanApprovalTimeoutError(PEAException):
    """Raised when human approval node times out."""

    def __init__(self, draft_id: str, timeout_seconds: int):
        super().__init__(
            message=f"草稿 '{draft_id}' 的人工审核已超时（{timeout_seconds}秒）",
            code="HUMAN_APPROVAL_TIMEOUT",
            details={"draft_id": draft_id, "timeout_seconds": timeout_seconds},
        )
