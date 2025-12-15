import { useState } from 'react'
import { Save, Key, User, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Settings() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'system', name: 'System', icon: Key },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 mt-1">Manage your account and system settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-600 text-white'
                      : 'text-gray-300 hover:bg-dark-200 hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5 mr-3" />
                  {tab.name}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          <div className="bg-dark-100 border border-dark-200 rounded-lg p-6">
            {activeTab === 'profile' && <ProfileSettings user={user} />}
            {activeTab === 'security' && <SecuritySettings />}
            {activeTab === 'system' && <SystemSettings />}
          </div>
        </div>
      </div>
    </div>
  )
}

function ProfileSettings({ user }) {
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    fullName: user?.full_name || '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    alert('Profile update functionality coming soon!')
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">Profile Settings</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Username
          </label>
          <input
            type="text"
            value={formData.username}
            disabled
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="mt-1 text-xs text-gray-400">Username cannot be changed</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Email
          </label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Full Name
          </label>
          <input
            type="text"
            value={formData.fullName}
            onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <button
          type="submit"
          className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
        >
          <Save className="w-4 h-4 mr-2" />
          Save Changes
        </button>
      </form>
    </div>
  )
}

function SecuritySettings() {
  const [formData, setFormData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (formData.newPassword !== formData.confirmPassword) {
      alert('Passwords do not match!')
      return
    }
    alert('Password change functionality coming soon!')
  }

  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">Security Settings</h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Current Password
          </label>
          <input
            type="password"
            value={formData.currentPassword}
            onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            New Password
          </label>
          <input
            type="password"
            value={formData.newPassword}
            onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Confirm New Password
          </label>
          <input
            type="password"
            value={formData.confirmPassword}
            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
            className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <button
          type="submit"
          className="flex items-center px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded"
        >
          <Key className="w-4 h-4 mr-2" />
          Change Password
        </button>
      </form>

      <div className="mt-8 p-4 bg-yellow-500 bg-opacity-10 border border-yellow-500 rounded-lg">
        <p className="text-yellow-400 text-sm">
          <strong>Warning:</strong> If you're still using the default 'admin' password,
          please change it immediately to secure your system.
        </p>
      </div>
    </div>
  )
}

function SystemSettings() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-white mb-6">System Settings</h2>

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-white mb-4">Paths Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                TOPGEN_VARLIB
              </label>
              <input
                type="text"
                defaultValue="/var/lib/topgen"
                disabled
                className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                TOPGEN_ETC
              </label>
              <input
                type="text"
                defaultValue="/etc/topgen"
                disabled
                className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white disabled:opacity-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                GREYBOX_ETC
              </label>
              <input
                type="text"
                defaultValue="/etc/greybox"
                disabled
                className="w-full px-4 py-2 bg-dark-50 border border-dark-200 rounded-lg text-white disabled:opacity-50"
              />
            </div>
          </div>
        </div>

        <div className="p-4 bg-blue-500 bg-opacity-10 border border-blue-500 rounded-lg">
          <p className="text-blue-400 text-sm">
            <strong>Note:</strong> System configuration editing will be available in a future update.
            For now, modify settings in the backend .env file.
          </p>
        </div>
      </div>
    </div>
  )
}
