import { useState } from 'react';
import { X, Save, Loader2, Eye, EyeOff, Check, AlertCircle } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { userService } from '../../services/userService';
import { useSuccessToast } from '../ui/Toast';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

interface PasswordValidation {
  minLength: boolean;
  hasUppercase: boolean;
  hasLowercase: boolean;
  hasNumber: boolean;
  passwordsMatch: boolean;
}

export function ChangePasswordModal({ isOpen, onClose }: ChangePasswordModalProps) {
  const [formData, setFormData] = useState<PasswordFormData>({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showValidation, setShowValidation] = useState(false);
  const showSuccess = useSuccessToast();

  const validatePassword = (password: string): PasswordValidation => {
    return {
      minLength: password.length >= 8,
      hasUppercase: /[A-Z]/.test(password),
      hasLowercase: /[a-z]/.test(password),
      hasNumber: /\d/.test(password),
      passwordsMatch: password === formData.confirmPassword
    };
  };

  const validation = validatePassword(formData.newPassword);

  const isFormValid = () => {
    return (
      formData.currentPassword.length > 0 &&
      formData.newPassword.length > 0 &&
      formData.confirmPassword.length > 0 &&
      validation.minLength &&
      validation.hasUppercase &&
      validation.hasLowercase &&
      validation.hasNumber &&
      validation.passwordsMatch &&
      formData.currentPassword !== formData.newPassword
    );
  };

  const handleInputChange = (field: keyof PasswordFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Show validation hints when user starts typing new password
    if (field === 'newPassword' && value.length > 0) {
      setShowValidation(true);
    }
    
    // Clear field-specific errors
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const togglePasswordVisibility = (field: keyof typeof showPasswords) => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
  };

  const handleSubmit = async () => {
    // Validate form
    const newErrors: Record<string, string> = {};
    
    if (!formData.currentPassword) {
      newErrors.currentPassword = 'Current password is required';
    }
    
    if (!formData.newPassword) {
      newErrors.newPassword = 'New password is required';
    } else if (!validation.minLength || !validation.hasUppercase || !validation.hasLowercase || !validation.hasNumber) {
      newErrors.newPassword = 'Password does not meet requirements';
    }
    
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your new password';
    } else if (!validation.passwordsMatch) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    if (formData.currentPassword === formData.newPassword) {
      newErrors.newPassword = 'New password must be different from current password';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setIsLoading(true);
    try {
      await userService.changePassword(formData.currentPassword, formData.newPassword);
      
      // Success feedback
      showSuccess('Password changed successfully!');
      
      // Reset form and close modal
      setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setShowValidation(false);
      setErrors({});
      onClose();
    } catch (error: any) {
      // Handle specific error messages
      if (error.message?.includes('current password')) {
        setErrors({ currentPassword: 'Current password is incorrect' });
      } else {
        setErrors({ general: 'Failed to change password. Please try again.' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setFormData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    setShowValidation(false);
    setErrors({});
    setShowPasswords({ current: false, new: false, confirm: false });
    onClose();
  };

  const ValidationItem = ({ isValid, text }: { isValid: boolean; text: string }) => (
    <div className={`flex items-center gap-2 text-sm ${isValid ? 'text-green-600' : 'text-[hsl(var(--text))] opacity-60'}`}>
      {isValid ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
      <span>{text}</span>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleCancel} title="Change Password" size="sm">
      <div className="space-y-6">
        {errors.general && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-600">
            {errors.general}
          </div>
        )}

        {/* Current Password */}
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
            Current Password
          </label>
          <div className="relative">
            <Input
              type={showPasswords.current ? 'text' : 'password'}
              value={formData.currentPassword}
              onChange={(e) => handleInputChange('currentPassword', e.target.value)}
              placeholder="Enter your current password"
              error={errors.currentPassword}
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('current')}
              className="absolute right-3 top-3 text-[hsl(var(--text))] opacity-60 hover:opacity-100"
            >
              {showPasswords.current ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {/* New Password */}
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
            New Password
          </label>
          <div className="relative">
            <Input
              type={showPasswords.new ? 'text' : 'password'}
              value={formData.newPassword}
              onChange={(e) => handleInputChange('newPassword', e.target.value)}
              placeholder="Enter your new password"
              error={errors.newPassword}
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('new')}
              className="absolute right-3 top-3 text-[hsl(var(--text))] opacity-60 hover:opacity-100"
            >
              {showPasswords.new ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {/* Password Requirements */}
          {showValidation && (
            <div className="mt-3 p-3 bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-md space-y-2">
              <div className="text-xs font-medium text-[hsl(var(--text))] opacity-80 mb-2">
                Password Requirements:
              </div>
              <ValidationItem isValid={validation.minLength} text="At least 8 characters" />
              <ValidationItem isValid={validation.hasUppercase} text="One uppercase letter" />
              <ValidationItem isValid={validation.hasLowercase} text="One lowercase letter" />
              <ValidationItem isValid={validation.hasNumber} text="One number" />
            </div>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] mb-2">
            Confirm New Password
          </label>
          <div className="relative">
            <Input
              type={showPasswords.confirm ? 'text' : 'password'}
              value={formData.confirmPassword}
              onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
              placeholder="Confirm your new password"
              error={errors.confirmPassword}
            />
            <button
              type="button"
              onClick={() => togglePasswordVisibility('confirm')}
              className="absolute right-3 top-3 text-[hsl(var(--text))] opacity-60 hover:opacity-100"
            >
              {showPasswords.confirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          {/* Password Match Indicator */}
          {formData.confirmPassword.length > 0 && (
            <div className={`mt-2 text-sm flex items-center gap-2 ${
              validation.passwordsMatch ? 'text-green-600' : 'text-red-600'
            }`}>
              {validation.passwordsMatch ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
              <span>{validation.passwordsMatch ? 'Passwords match' : 'Passwords do not match'}</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || !isFormValid()}
            className="flex-1"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Changing...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Change Password
              </>
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}