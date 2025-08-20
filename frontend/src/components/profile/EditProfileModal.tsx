import { useState, useEffect } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { AvatarUpload } from './AvatarUpload';
import { userService, type UserProfile, type UserUpdateData } from '../../services/userService';
import { useErrorToast } from '../ui/Toast';

interface EditProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile;
  onSave: (updatedProfile: UserProfile) => void;
}

export function EditProfileModal({ isOpen, onClose, profile, onSave }: EditProfileModalProps) {
  const [formData, setFormData] = useState<UserUpdateData>({
    first_name: profile.first_name || '',
    last_name: profile.last_name || '',
    display_name: profile.display_name || '',
    avatar_url: profile.avatar_url || ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const showError = useErrorToast();

  // Reset form when profile changes or modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        first_name: profile.first_name || '',
        last_name: profile.last_name || '',
        display_name: profile.display_name || '',
        avatar_url: profile.avatar_url || ''
      });
      setErrors({});
    }
  }, [isOpen, profile]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (formData.first_name && formData.first_name.length < 1) {
      newErrors.first_name = 'First name must be at least 1 character';
    }
    if (formData.first_name && formData.first_name.length > 50) {
      newErrors.first_name = 'First name must be less than 50 characters';
    }

    if (formData.last_name && formData.last_name.length < 1) {
      newErrors.last_name = 'Last name must be at least 1 character';
    }
    if (formData.last_name && formData.last_name.length > 50) {
      newErrors.last_name = 'Last name must be less than 50 characters';
    }

    if (formData.display_name && formData.display_name.length < 1) {
      newErrors.display_name = 'Display name must be at least 1 character';
    }
    if (formData.display_name && formData.display_name.length > 100) {
      newErrors.display_name = 'Display name must be less than 100 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (field: keyof UserUpdateData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleAvatarUpload = async (file: File) => {
    setIsUploadingAvatar(true);
    try {
      const result = await userService.uploadAvatar(file);
      setFormData(prev => ({ ...prev, avatar_url: result.avatar_url }));
    } catch (error) {
      console.error('Avatar upload failed:', error);
      showError('Failed to upload avatar. Please try again.');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleAvatarRemove = async () => {
    setIsUploadingAvatar(true);
    try {
      await userService.removeAvatar();
      setFormData(prev => ({ ...prev, avatar_url: '' }));
    } catch (error) {
      console.error('Avatar removal failed:', error);
      showError('Failed to remove avatar. Please try again.');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    try {
      // Only send fields that have values
      const updateData: UserUpdateData = {};
      if (formData.first_name?.trim()) updateData.first_name = formData.first_name.trim();
      if (formData.last_name?.trim()) updateData.last_name = formData.last_name.trim();
      if (formData.display_name?.trim()) updateData.display_name = formData.display_name.trim();
      if (formData.avatar_url) updateData.avatar_url = formData.avatar_url;

      const updatedProfile = await userService.updateProfile(updateData);
      onSave(updatedProfile);
      onClose();
    } catch (error) {
      console.error('Profile update failed:', error);
      showError('Failed to update profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setFormData({
      first_name: profile.first_name || '',
      last_name: profile.last_name || '',
      display_name: profile.display_name || '',
      avatar_url: profile.avatar_url || ''
    });
    setErrors({});
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={handleCancel} title="Edit Profile" size="sm">
      <div>

        <div className="space-y-6">
          {/* Avatar Upload */}
          <AvatarUpload
            currentAvatarUrl={formData.avatar_url}
            onUpload={handleAvatarUpload}
            onRemove={handleAvatarRemove}
            isUploading={isUploadingAvatar}
          />

          {/* Personal Information */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
                First Name
              </label>
              <Input
                value={formData.first_name}
                onChange={(e) => handleInputChange('first_name', e.target.value)}
                placeholder="Enter your first name"
                error={errors.first_name}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
                Last Name
              </label>
              <Input
                value={formData.last_name}
                onChange={(e) => handleInputChange('last_name', e.target.value)}
                placeholder="Enter your last name"
                error={errors.last_name}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
                Display Name
              </label>
              <Input
                value={formData.display_name}
                onChange={(e) => handleInputChange('display_name', e.target.value)}
                placeholder="Enter your display name"
                error={errors.display_name}
              />
              <p className="text-xs text-[hsl(var(--text))] opacity-60 mt-1">
                This is how your name will appear to others
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button
              variant="outline"
              onClick={handleCancel}
              disabled={isLoading || isUploadingAvatar}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={isLoading || isUploadingAvatar}
              className="flex-1"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}