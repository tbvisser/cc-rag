interface SuggestionCardsProps {
  onSelect: (message: string) => void
}

const suggestions = [
  {
    title: 'Industry Status report',
    description: 'Get the latest status of your industry',
    gradient: 'from-blue-500/10 to-cyan-500/10 border-blue-200',
  },
  {
    title: 'Customer value analysis',
    description: 'Analyze value delivered to customers',
    gradient: 'from-purple-500/10 to-pink-500/10 border-purple-200',
  },
  {
    title: 'Risk analysis on BOM',
    description: 'Assess risks in your bill of materials',
    gradient: 'from-orange-500/10 to-red-500/10 border-orange-200',
  },
  {
    title: 'Weekly Supply KPI update',
    description: 'Review this week\'s supply chain KPIs',
    gradient: 'from-green-500/10 to-emerald-500/10 border-green-200',
  },
]

export function SuggestionCards({ onSelect }: SuggestionCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {suggestions.map((s) => (
        <button
          key={s.title}
          onClick={() => onSelect(s.title)}
          className={`rounded-xl border bg-gradient-to-br p-4 text-left transition-shadow hover:shadow-md ${s.gradient}`}
        >
          <p className="text-sm font-medium">{s.title}</p>
          <p className="mt-1 text-xs text-muted-foreground">{s.description}</p>
        </button>
      ))}
    </div>
  )
}
