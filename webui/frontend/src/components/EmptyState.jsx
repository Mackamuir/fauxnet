/**
 * Universal empty state component
 * @param {React.Component} icon - Icon component from lucide-react
 * @param {string} title - Main message
 * @param {string} subtitle - Optional secondary message
 * @param {React.Component} action - Optional action button/component
 */
export default function EmptyState({ icon: Icon, title, subtitle, action }) {
  return (
    <div className="bg-dark-100 border border-dark-200 rounded-lg p-12 text-center">
      {Icon && <Icon className="w-16 h-16 text-gray-600 mx-auto mb-4" />}
      <p className="text-gray-400 text-lg mb-2">{title}</p>
      {subtitle && <p className="text-gray-500 text-sm">{subtitle}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
