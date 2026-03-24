interface OIPageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function OIPageHeader({ title, subtitle, actions }: OIPageHeaderProps) {
  return (
    <div className="flex items-end justify-between mb-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-on-surface uppercase font-mono">{title}</h1>
        {subtitle && <p className="text-sm text-on-surface-variant mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}
