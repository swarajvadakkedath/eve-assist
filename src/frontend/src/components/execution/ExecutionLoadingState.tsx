function ExecutionLoadingState() {
  return (
    <div className="pr-exec-loading" role="status" aria-label="Loading execution">
      <div className="pr-exec-loading-skeleton" />
      <div className="pr-exec-loading-skeleton" />
      <div className="pr-exec-loading-skeleton" />
    </div>
  );
}

export default ExecutionLoadingState;
