interface OIErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export function OIErrorState({ message, onRetry }: OIErrorStateProps) {
  return (
    <div className="rounded-2xl border border-error/20 bg-error/5 px-5 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-error text-lg">⚠</span>
        <span className="text-sm font-mono text-error">{message}</span>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs font-mono text-error/70 hover:text-error underline transition-colors ml-4"
        >
          Retry
        </button>
      )}
    </div>
  );
}
