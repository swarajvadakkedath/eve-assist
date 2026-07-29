function ConversationLoadingState() {
  return (
    <div className="pr-conv-loading" role="status" aria-label="Loading messages">
      <div className="pr-conv-loading-skeleton" />
      <div className="pr-conv-loading-skeleton" />
      <div className="pr-conv-loading-skeleton" />
    </div>
  );
}

export default ConversationLoadingState;
