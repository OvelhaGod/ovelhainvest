"use client";

interface Tab { label: string; value: string; }

interface OITabBarProps {
  tabs: Tab[];
  activeTab: string;
  onChange: (value: string) => void;
}

export function OITabBar({ tabs, activeTab, onChange }: OITabBarProps) {
  return (
    <div className="flex gap-1 p-1 glass-card-subtle rounded-full w-fit mb-6">
      {tabs.map((tab) => (
        <button
          key={tab.value}
          onClick={() => onChange(tab.value)}
          className={`px-4 py-1.5 rounded-full text-xs font-mono font-medium transition-all ${
            activeTab === tab.value
              ? "bg-primary/10 text-primary"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
