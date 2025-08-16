import { useState, useEffect } from 'react';
import { Download, Trash2, LogOut, Key, Monitor } from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { LoadingSpinner } from '../components/ui';
import { ProfileInfo } from '../components/profile/ProfileInfo';
import { EditProfileModal } from '../components/profile/EditProfileModal';
import { ChangePasswordModal } from '../components/profile/ChangePasswordModal';
import { SessionManagementModal } from '../components/profile/SessionManagementModal';
import { userService, type UserProfile, type UserStats } from '../services/userService';
import { useAuthStore } from '../stores/authStore';

export function Profile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { logout } = useAuthStore();

  // Load profile data
  useEffect(() => {
    loadProfileData();
  }, []);

  const loadProfileData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const [profileData, statsData] = await Promise.all([
        userService.getCurrentUserProfile(),
        userService.getUserStats().catch(() => null) // Stats might not be available
      ]);
      
      setProfile(profileData);
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load profile:', error);
      setError('Failed to load profile data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProfileUpdate = (updatedProfile: UserProfile) => {
    setProfile(updatedProfile);
    // Update auth store with new user data
    useAuthStore.getState().updateUser({
      displayName: updatedProfile.display_name,
      avatarUrl: updatedProfile.avatar_url
    });
  };

  const handleExportData = async () => {
    try {
      setIsExporting(true);
      const blob = await userService.exportUserData();
      
      // Create download link
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance-tracker-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export data. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    const confirmMessage = 'Are you sure you want to delete your account? This action cannot be undone and will permanently delete all your financial data.';
    
    if (!confirm(confirmMessage)) {
      return;
    }

    // Double confirmation
    const secondConfirm = prompt('Type "DELETE" to confirm account deletion:');
    if (secondConfirm !== 'DELETE') {
      alert('Account deletion cancelled.');
      return;
    }

    try {
      await userService.deactivateAccount();
      alert('Your account has been deactivated. You will now be logged out.');
      logout();
    } catch (error) {
      console.error('Account deletion failed:', error);
      alert('Failed to delete account. Please contact support.');
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat().format(num);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'hsl(var(--bg))' }}>
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'hsl(var(--bg))' }}>
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || 'Failed to load profile'}</p>
          <Button onClick={loadProfileData}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-8" style={{ backgroundColor: 'hsl(var(--bg))', color: 'hsl(var(--text))' }}>
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[hsl(var(--text))]">My Profile</h1>
          <p className="mt-2 text-[hsl(var(--text))] opacity-70">Manage your personal information and account settings</p>
        </div>

        <div className="space-y-6">
          {/* Profile Information */}
          <ProfileInfo
            profile={profile}
            onEdit={() => setIsEditModalOpen(true)}
          />

          {/* Account Statistics */}
          {stats && (
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-semibold text-[hsl(var(--text))] mb-4">Account Statistics</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="text-center p-4 bg-[hsl(var(--surface))] rounded-lg">
                    <div className="text-2xl font-bold text-[hsl(var(--brand))]">
                      {formatNumber(stats.total_transactions)}
                    </div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Total Transactions</div>
                  </div>
                  <div className="text-center p-4 bg-[hsl(var(--surface))] rounded-lg">
                    <div className="text-2xl font-bold text-[hsl(var(--brand))]">
                      {formatNumber(stats.total_accounts)}
                    </div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Connected Accounts</div>
                  </div>
                  <div className="text-center p-4 bg-[hsl(var(--surface))] rounded-lg">
                    <div className="text-2xl font-bold text-[hsl(var(--brand))]">
                      {formatNumber(stats.account_age_days)}
                    </div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Days as Member</div>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* Security Actions */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-[hsl(var(--text))] mb-4">Security & Privacy</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Key className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">Password</div>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70">Change your account password</div>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setIsChangePasswordModalOpen(true)}
                  >
                    Change Password
                  </Button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Monitor className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">Active Sessions</div>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70">Manage your login sessions</div>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setIsSessionModalOpen(true)}
                  >
                    Manage Sessions
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          {/* Data Management */}
          <Card>
            <div className="p-6">
              <h2 className="text-xl font-semibold text-[hsl(var(--text))] mb-4">Data Management</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Download className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">Export Data</div>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70">Download all your financial data</div>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleExportData}
                    disabled={isExporting}
                  >
                    {isExporting ? 'Exporting...' : 'Export'}
                  </Button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Trash2 className="h-5 w-5 text-red-500" />
                    <div>
                      <div className="font-medium text-[hsl(var(--text))]">Delete Account</div>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70">Permanently delete your account and all data</div>
                    </div>
                  </div>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={handleDeleteAccount}
                    className="text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
                  >
                    Delete Account
                  </Button>
                </div>
              </div>
            </div>
          </Card>

          {/* Logout */}
          <Card>
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <LogOut className="h-5 w-5 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="font-medium text-[hsl(var(--text))]">Sign Out</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">Sign out of your account</div>
                  </div>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={logout}
                >
                  Sign Out
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Edit Profile Modal */}
      <EditProfileModal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        profile={profile}
        onSave={handleProfileUpdate}
      />

      {/* Change Password Modal */}
      <ChangePasswordModal
        isOpen={isChangePasswordModalOpen}
        onClose={() => setIsChangePasswordModalOpen(false)}
      />

      {/* Session Management Modal */}
      <SessionManagementModal
        isOpen={isSessionModalOpen}
        onClose={() => setIsSessionModalOpen(false)}
      />
    </div>
  );
}