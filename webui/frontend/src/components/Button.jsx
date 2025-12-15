import { Loader2 } from 'lucide-react'

/**
 * Universal button component with consistent styling
 * @param {React.Component} icon - Optional icon component
 * @param {string} children - Button text
 * @param {function} onClick - Click handler
 * @param {boolean} loading - Show loading state
 * @param {boolean} disabled - Disabled state
 * @param {string} variant - Button variant: 'primary', 'secondary', 'success', 'danger', 'warning', 'ghost'
 * @param {string} size - Button size: 'sm', 'md' (default), 'lg'
 * @param {string} className - Additional classes
 */
export default function Button({
  icon: Icon,
  children,
  onClick,
  loading = false,
  disabled = false,
  variant = "primary",
  size = "md",
  className = "",
  ...props
}) {
  const variants = {
    primary: "bg-primary-600 hover:bg-primary-700 text-white",
    secondary: "bg-dark-200 hover:bg-dark-300 text-white",
    success: "bg-green-600 hover:bg-green-700 text-white",
    danger: "bg-red-600 hover:bg-red-700 text-white",
    warning: "bg-yellow-600 hover:bg-yellow-700 text-white",
    ghost: "bg-transparent hover:bg-dark-200 text-gray-300 border border-dark-300"
  }

  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base"
  }

  const iconSizes = {
    sm: "w-3 h-3",
    md: "w-4 h-4",
    lg: "w-5 h-5"
  }

  const isDisabled = disabled || loading

  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      className={`
        flex items-center justify-center gap-2
        rounded font-medium
        transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]}
        ${sizes[size]}
        ${className}
      `}
      {...props}
    >
      {loading ? (
        <Loader2 className={`${iconSizes[size]} animate-spin`} />
      ) : (
        Icon && <Icon className={iconSizes[size]} />
      )}
      {children}
    </button>
  )
}
