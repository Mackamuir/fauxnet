import { X } from 'lucide-react'

/**
 * Universal modal component
 * @param {boolean} isOpen - Whether modal is visible
 * @param {function} onClose - Close handler
 * @param {string} title - Modal title
 * @param {React.Component} children - Modal content
 * @param {React.Component} footer - Optional footer content (buttons, etc)
 * @param {string} size - Modal size: 'sm', 'md' (default), 'lg', 'xl', 'full'
 */
export default function Modal({ isOpen, onClose, title, children, footer, size = "md" }) {
  if (!isOpen) return null

  const sizeClasses = {
    sm: "max-w-md",
    md: "max-w-2xl",
    lg: "max-w-4xl",
    xl: "max-w-6xl",
    full: "max-w-full mx-4"
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className={`bg-dark-100 border border-dark-200 rounded-lg ${sizeClasses[size]} w-full max-h-[90vh] flex flex-col`}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-200">
          <h3 className="text-xl font-semibold text-white">{title}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 p-6 border-t border-dark-200">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
