import { RefreshCw } from 'lucide-react'

/**
 * Universal loading screen component
 * @param {string} message - Optional loading message (default: "Loading...")
 * @param {string} size - Size of spinner: 'sm', 'md' (default), 'lg'
 */
export default function LoadingScreen({ message = "Loading...", size = "md" }) {
  const sizeClasses = {
    sm: "w-5 h-5",
    md: "w-6 h-6",
    lg: "w-8 h-8"
  }

  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center space-y-3">
        <RefreshCw className={`${sizeClasses[size]} text-primary-500 animate-spin`} />
        <span className="text-gray-400">{message}</span>
      </div>
    </div>
  )
}
