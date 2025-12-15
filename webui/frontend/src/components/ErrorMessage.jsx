import { AlertCircle } from 'lucide-react'

/**
 * Universal error message component
 * @param {string} title - Error title (default: "Error")
 * @param {string} message - Error message
 * @param {string} variant - Variant: 'error' (default), 'warning', 'info'
 */
export default function ErrorMessage({ title = "Error", message, variant = "error" }) {
  const variants = {
    error: {
      bg: "bg-red-500 bg-opacity-10",
      border: "border-red-500",
      titleColor: "text-red-400",
      messageColor: "text-red-300",
      iconColor: "text-red-500"
    },
    warning: {
      bg: "bg-yellow-500 bg-opacity-10",
      border: "border-yellow-500",
      titleColor: "text-yellow-400",
      messageColor: "text-yellow-300",
      iconColor: "text-yellow-500"
    },
    info: {
      bg: "bg-blue-500 bg-opacity-10",
      border: "border-blue-500",
      titleColor: "text-blue-400",
      messageColor: "text-blue-300",
      iconColor: "text-blue-500"
    }
  }

  const style = variants[variant] || variants.error

  return (
    <div className={`${style.bg} border ${style.border} rounded-lg p-4`}>
      <div className="flex items-start">
        <AlertCircle className={`w-5 h-5 ${style.iconColor} mr-3 mt-0.5 flex-shrink-0`} />
        <div className="flex-1">
          <p className={`${style.titleColor} font-medium`}>{title}</p>
          <p className={`${style.messageColor} text-sm mt-1`}>{message}</p>
        </div>
      </div>
    </div>
  )
}
