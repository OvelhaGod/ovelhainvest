interface OIEmptyStateProps {
  title?: string;
  description: string;
  action?: React.ReactNode;
}

export function OIEmptyState({ title, description, action }: OIEmptyStateProps) {
  return (
    <div className="py-16 text-center">
      <p className="text-3xl mb-3 opacity-20">—</p>
      {title && <p className="text-sm font-mono text-on-surface mb-1">{title}</p>}
      <p className="text-sm text-outline">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
