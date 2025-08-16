import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, Mail, Lock, User } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useAuthStore } from '../../stores/authStore';
import type { RegisterCredentials } from '../../types/auth';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin?: () => void;
}

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  displayName: string;
}

export function RegisterForm({ onSuccess, onSwitchToLogin }: RegisterFormProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const { register: registerUser, isLoading, error, clearError } = useAuthStore();

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>();

  const password = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    try {
      clearError();
      // Extract credentials without confirmPassword
      const credentials = {
        email: data.email,
        password: data.password,
        displayName: data.displayName
      };
      await registerUser(credentials as RegisterCredentials);
      // Note: With Supabase email confirmation, user needs to check email before login
      onSuccess?.();
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <div className="w-full max-w-md space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Create Account</h2>
        <p className="mt-2 text-gray-600">Start tracking your finances today</p>
      </div>

      {error && (
        <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="relative">
          <Input
            {...register('displayName', {
              required: 'Name is required',
              minLength: {
                value: 2,
                message: 'Name must be at least 2 characters',
              },
            })}
            type="text"
            label="Full Name"
            placeholder="Enter your full name"
            error={errors.displayName?.message}
            className="!pl-10"
            autoComplete="name"
          />
          <div className="absolute top-0 bottom-0 left-3 flex items-center pointer-events-none">
            <User className="h-4 w-4 text-gray-400" />
          </div>
        </div>

        <div className="relative">
          <Input
            {...register('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email address',
              },
            })}
            type="email"
            label="Email"
            placeholder="Enter your email"
            error={errors.email?.message}
            className="!pl-10"
            autoComplete="email"
          />
          <div className="absolute top-0 bottom-0 left-3 flex items-center pointer-events-none">
            <Mail className="h-4 w-4 text-gray-400" />
          </div>
        </div>

        <div className="relative">
          <Input
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters',
              },
              pattern: {
                value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                message: 'Password must contain uppercase, lowercase, and number',
              },
            })}
            type={showPassword ? 'text' : 'password'}
            label="Password"
            placeholder="Create a password"
            error={errors.password?.message}
            className="!pl-10 !pr-10"
            autoComplete="new-password"
          />
          <div className="absolute top-0 bottom-0 left-3 flex items-center pointer-events-none">
            <Lock className="h-4 w-4 text-gray-400" />
          </div>
          <div className="absolute top-0 bottom-0 right-3 flex items-center">
            <button
              type="button"
              className="text-gray-400 hover:text-gray-600"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <div className="relative">
          <Input
            {...register('confirmPassword', {
              required: 'Please confirm your password',
              validate: (value) =>
                value === password || 'Passwords do not match',
            })}
            type={showConfirmPassword ? 'text' : 'password'}
            label="Confirm Password"
            placeholder="Confirm your password"
            error={errors.confirmPassword?.message}
            className="!pl-10 !pr-10"
            autoComplete="new-password"
          />
          <div className="absolute top-0 bottom-0 left-3 flex items-center pointer-events-none">
            <Lock className="h-4 w-4 text-gray-400" />
          </div>
          <div className="absolute top-0 bottom-0 right-3 flex items-center">
            <button
              type="button"
              className="text-gray-400 hover:text-gray-600"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              {showConfirmPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        <div className="text-xs text-gray-500">
          Password must contain:
          <ul className="mt-1 space-y-1">
            <li className="flex items-center">
              <span className="w-1 h-1 bg-gray-300 rounded-full mr-2"></span>
              At least 8 characters
            </li>
            <li className="flex items-center">
              <span className="w-1 h-1 bg-gray-300 rounded-full mr-2"></span>
              One uppercase letter
            </li>
            <li className="flex items-center">
              <span className="w-1 h-1 bg-gray-300 rounded-full mr-2"></span>
              One lowercase letter
            </li>
            <li className="flex items-center">
              <span className="w-1 h-1 bg-gray-300 rounded-full mr-2"></span>
              One number
            </li>
          </ul>
        </div>

        <Button
          type="submit"
          className="w-full"
          loading={isLoading}
          disabled={isLoading}
        >
          Create Account
        </Button>
      </form>

      {onSwitchToLogin && (
        <div className="text-center">
          <p className="text-sm text-gray-600">
            Already have an account?{' '}
            <button
              type="button"
              className="font-medium text-primary-600 hover:text-primary-700"
              onClick={onSwitchToLogin}
            >
              Sign in
            </button>
          </p>
        </div>
      )}
    </div>
  );
}