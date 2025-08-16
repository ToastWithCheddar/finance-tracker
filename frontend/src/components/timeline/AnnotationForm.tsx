import React, { useState } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useCreateAnnotation, useUpdateAnnotation } from '../../hooks/useTimeline';
import type { TimelineAnnotation, TimelineAnnotationCreate, TimelineAnnotationUpdate } from '../../services/timelineService';

interface AnnotationFormProps {
  isOpen: boolean;
  onClose: () => void;
  annotation?: TimelineAnnotation;
  initialDate?: string;
}

const ICON_OPTIONS = [
  { value: '📝', label: '📝 Note' },
  { value: '💼', label: '💼 Work' },
  { value: '🏠', label: '🏠 Home' },
  { value: '🚗', label: '🚗 Car' },
  { value: '🎓', label: '🎓 Education' },
  { value: '💰', label: '💰 Money' },
  { value: '🎉', label: '🎉 Celebration' },
  { value: '⚠️', label: '⚠️ Important' },
  { value: '💡', label: '💡 Idea' },
  { value: '🎯', label: '🎯 Goal' },
];

const COLOR_OPTIONS = [
  { value: '#6366f1', label: 'Indigo' },
  { value: '#10b981', label: 'Green' },
  { value: '#f59e0b', label: 'Amber' },
  { value: '#ef4444', label: 'Red' },
  { value: '#3b82f6', label: 'Blue' },
  { value: '#8b5cf6', label: 'Purple' },
  { value: '#06b6d4', label: 'Cyan' },
  { value: '#84cc16', label: 'Lime' },
];

export function AnnotationForm({ isOpen, onClose, annotation, initialDate }: AnnotationFormProps) {
  const isEditing = Boolean(annotation);
  const createMutation = useCreateAnnotation();
  const updateMutation = useUpdateAnnotation();

  const [formData, setFormData] = useState({
    date: annotation?.date || initialDate || new Date().toISOString().split('T')[0],
    title: annotation?.title || '',
    description: annotation?.description || '',
    icon: annotation?.icon || '📝',
    color: annotation?.color || '#6366f1',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const resetForm = () => {
    setFormData({
      date: initialDate || new Date().toISOString().split('T')[0],
      title: '',
      description: '',
      icon: '📝',
      color: '#6366f1',
    });
    setErrors({});
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }

    if (!formData.date) {
      newErrors.date = 'Date is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      if (isEditing && annotation) {
        const updateData: TimelineAnnotationUpdate = {
          date: formData.date,
          title: formData.title.trim(),
          description: formData.description.trim() || undefined,
          icon: formData.icon,
          color: formData.color,
        };

        await updateMutation.mutateAsync({ id: annotation.id, data: updateData });
      } else {
        const createData: TimelineAnnotationCreate = {
          date: formData.date,
          title: formData.title.trim(),
          description: formData.description.trim() || undefined,
          icon: formData.icon,
          color: formData.color,
        };

        await createMutation.mutateAsync(createData);
      }

      handleClose();
    } catch (error) {
      // Error handling is done in the mutation hooks
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={isEditing ? 'Edit Timeline Annotation' : 'Add Timeline Annotation'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Date Input */}
        <div>
          <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Date
          </label>
          <Input
            id="date"
            type="date"
            value={formData.date}
            onChange={(e) => handleInputChange('date', e.target.value)}
            error={errors.date}
            required
          />
        </div>

        {/* Title Input */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Title
          </label>
          <Input
            id="title"
            type="text"
            value={formData.title}
            onChange={(e) => handleInputChange('title', e.target.value)}
            placeholder="e.g., Started new job, Paid off car loan"
            error={errors.title}
            required
          />
        </div>

        {/* Description Input */}
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description
          </label>
          <textarea
            id="description"
            value={formData.description}
            onChange={(e) => handleInputChange('description', e.target.value)}
            placeholder="Optional details about this event..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
          />
        </div>

        {/* Icon Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Icon
          </label>
          <div className="grid grid-cols-5 gap-2">
            {ICON_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleInputChange('icon', option.value)}
                className={`p-2 text-center rounded-md border-2 transition-colors ${
                  formData.icon === option.value
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                }`}
                title={option.label}
              >
                <span className="text-lg">{option.value}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Color Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Color
          </label>
          <div className="flex gap-2 flex-wrap">
            {COLOR_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleInputChange('color', option.value)}
                className={`w-8 h-8 rounded-full border-2 transition-all ${
                  formData.color === option.value
                    ? 'border-gray-900 dark:border-white scale-110'
                    : 'border-gray-300 dark:border-gray-600 hover:scale-105'
                }`}
                style={{ backgroundColor: option.value }}
                title={option.label}
              />
            ))}
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex gap-3 pt-4">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={isLoading}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isLoading}
            className="flex-1"
          >
            {isLoading ? 'Saving...' : isEditing ? 'Update' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}