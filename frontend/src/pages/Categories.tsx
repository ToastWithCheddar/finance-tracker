import { useState, useEffect } from 'react';
import { 
  PlusIcon, 
  PencilIcon, 
  TrashIcon, 
  ChevronRightIcon,
  ChevronDownIcon 
} from '@heroicons/react/24/outline';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { categoryService } from '../services/categoryService';
import type { Category, CategoryWithChildren, CreateCategoryRequest, UpdateCategoryRequest } from '../types/category';

interface CategoryFormData {
  name: string;
  description: string;
  emoji: string;
  color: string;
  parent_id?: string;
}

export function Categories() {
  const [categories, setCategories] = useState<CategoryWithChildren[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  
  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null);
  
  // Form states
  const [formData, setFormData] = useState<CategoryFormData>({
    name: '',
    description: '',
    emoji: '',
    color: '#3B82F6',
    parent_id: undefined
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const hierarchy = await categoryService.getCategoriesHierarchy({ include_system: true });
      setCategories(hierarchy);
    } catch (error) {
      console.error('Failed to load categories:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleCategoryExpansion = (categoryId: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(categoryId)) {
      newExpanded.delete(categoryId);
    } else {
      newExpanded.add(categoryId);
    }
    setExpandedCategories(newExpanded);
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Category name is required';
    } else if (formData.name.length > 100) {
      errors.name = 'Category name must be less than 100 characters';
    }

    if (formData.description && formData.description.length > 500) {
      errors.description = 'Description must be less than 500 characters';
    }

    if (formData.emoji && formData.emoji.length > 10) {
      errors.emoji = 'Emoji must be less than 10 characters';
    }

    if (formData.color && !/^#[0-9A-Fa-f]{6}$/.test(formData.color)) {
      errors.color = 'Please enter a valid hex color';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleCreate = async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const createData: CreateCategoryRequest = {
        name: formData.name,
        description: formData.description || undefined,
        emoji: formData.emoji || undefined,
        color: formData.color,
        parent_id: formData.parent_id
      };

      await categoryService.createCategory(createData);
      await loadCategories();
      setIsCreateModalOpen(false);
      resetForm();
    } catch (error) {
      console.error('Failed to create category:', error);
      setFormErrors({ submit: 'Failed to create category. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editingCategory || !validateForm()) return;

    setIsSubmitting(true);
    try {
      const updateData: UpdateCategoryRequest = {
        name: formData.name,
        description: formData.description || undefined,
        emoji: formData.emoji || undefined,
        color: formData.color,
        parent_id: formData.parent_id
      };

      await categoryService.updateCategory(editingCategory.id, updateData);
      await loadCategories();
      setIsEditModalOpen(false);
      setEditingCategory(null);
      resetForm();
    } catch (error) {
      console.error('Failed to update category:', error);
      setFormErrors({ submit: 'Failed to update category. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingCategory) return;

    setIsSubmitting(true);
    try {
      await categoryService.deleteCategory(deletingCategory.id);
      await loadCategories();
      setIsDeleteModalOpen(false);
      setDeletingCategory(null);
    } catch (error) {
      console.error('Failed to delete category:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openCreateModal = (parentId?: string) => {
    resetForm();
    setFormData(prev => ({ ...prev, parent_id: parentId }));
    setIsCreateModalOpen(true);
  };

  const openEditModal = (category: Category) => {
    setEditingCategory(category);
    setFormData({
      name: category.name,
      description: category.description || '',
      emoji: category.emoji || '',
      color: category.color || '#3B82F6',
      parent_id: category.parent_id
    });
    setIsEditModalOpen(true);
  };

  const openDeleteModal = (category: Category) => {
    setDeletingCategory(category);
    setIsDeleteModalOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      emoji: '',
      color: '#3B82F6',
      parent_id: undefined
    });
    setFormErrors({});
  };

  const renderCategory = (category: CategoryWithChildren, level: number = 0) => {
    const hasChildren = category.children.length > 0;
    const isExpanded = expandedCategories.has(category.id);
    const paddingLeft = level * 24;

    return (
      <div key={category.id} className="border-b last:border-b-0 border-[hsl(var(--border))]">
        <div 
          className="flex items-center justify-between p-4 hover:bg-[hsl(var(--border)/0.12)]"
          style={{ paddingLeft: `${16 + paddingLeft}px` }}
        >
          <div className="flex items-center flex-1 min-w-0">
            {hasChildren && (
              <button
                onClick={() => toggleCategoryExpansion(category.id)}
                className="mr-2 p-1 hover:bg-[hsl(var(--border)/0.35)] rounded"
              >
                {isExpanded ? (
                  <ChevronDownIcon className="h-4 w-4" />
                ) : (
                  <ChevronRightIcon className="h-4 w-4" />
                )}
              </button>
            )}
            
            {!hasChildren && <div className="w-6 mr-2" />}
            
            {category.emoji && (
              <span className="mr-3 text-lg">{category.emoji}</span>
            )}
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center">
                <h3 className="font-medium text-[hsl(var(--text))] truncate">
                  {category.name}
                </h3>
                {category.is_system && (
                  <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100 rounded-full">
                    System
                  </span>
                )}
              </div>
              {category.description && (
                <p className="text-sm text-[hsl(var(--text))] opacity-70 truncate">
                  {category.description}
                </p>
              )}
            </div>
            
            {category.color && (
              <div 
                className="w-4 h-4 rounded-full border mr-3 border-[hsl(var(--border))]"
                style={{ backgroundColor: category.color }}
              />
            )}
          </div>

          <div className="flex items-center space-x-2">
            {hasChildren && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => openCreateModal(category.id)}
                className="text-xs"
              >
                <PlusIcon className="h-3 w-3 mr-1" />
                Add Sub
              </Button>
            )}
            
            {!category.is_system && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openEditModal(category)}
                  className="text-xs"
                >
                  <PencilIcon className="h-3 w-3" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openDeleteModal(category)}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  <TrashIcon className="h-3 w-3" />
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Render children */}
        {hasChildren && isExpanded && (
          <div>
            {category.children.map(child => renderCategory(child, level + 1))}
          </div>
        )}
      </div>
    );
  };

  const renderCategoryForm = () => (
    <div className="space-y-4">
      {formErrors.submit && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
          {formErrors.submit}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-[hsl(var(--text))] opacity-80 mb-1">
          Name *
        </label>
        <Input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
          placeholder="Category name"
          className={formErrors.name ? 'border-red-300' : ''}
        />
        {formErrors.name && (
          <p className="mt-1 text-sm text-red-600">{formErrors.name}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-[hsl(var(--text))] opacity-80 mb-1">
          Description
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="Optional description"
          rows={3}
          maxLength={500}
          className={`w-full px-3 py-2 rounded-lg focus:ring-2 bg-[hsl(var(--surface))] text-[hsl(var(--text))] border border-[hsl(var(--border))] focus:ring-[hsl(var(--brand))] focus:border-[hsl(var(--brand))] ${
            formErrors.description ? 'border-red-300' : ''
          }`}
        />
        <div className="flex justify-between mt-1">
          {formErrors.description && (
            <p className="text-sm text-red-600">{formErrors.description}</p>
          )}
          <p className="text-xs ml-auto text-[hsl(var(--text))] opacity-60">
            {formData.description.length}/500
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] opacity-80 mb-1">
            Emoji
          </label>
          <Input
            type="text"
            value={formData.emoji}
            onChange={(e) => setFormData(prev => ({ ...prev, emoji: e.target.value }))}
            placeholder="🍔"
            maxLength={10}
            className={formErrors.emoji ? 'border-red-300' : ''}
          />
          {formErrors.emoji && (
            <p className="mt-1 text-sm text-red-600">{formErrors.emoji}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-[hsl(var(--text))] opacity-80 mb-1">
            Color
          </label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={formData.color}
              onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
              className="w-10 h-10 border rounded cursor-pointer border-[hsl(var(--border))] bg-[hsl(var(--surface))]"
            />
            <Input
              type="text"
              value={formData.color}
              onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
              placeholder="#3B82F6"
              className={`flex-1 ${formErrors.color ? 'border-red-300' : ''}`}
            />
          </div>
          {formErrors.color && (
            <p className="mt-1 text-sm text-red-600">{formErrors.color}</p>
          )}
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 rounded w-1/4 mb-6 bg-[hsl(var(--border)/0.35)]"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 rounded bg-[hsl(var(--border)/0.35)]"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[hsl(var(--text))]">Categories</h1>
            <p className="mt-1 text-[hsl(var(--text))] opacity-70">
              Manage your transaction categories
            </p>
          </div>
          <Button onClick={() => openCreateModal()}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Add Category
          </Button>
        </div>
      </div>

      <div className="rounded-lg shadow border bg-[hsl(var(--surface))] border-[hsl(var(--border))] text-[hsl(var(--text))]">
        {categories.length === 0 ? (
          <div className="p-8 text-center">
            <p className="opacity-70">No categories found</p>
          </div>
        ) : (
          <div>
            {categories.map(category => renderCategory(category))}
          </div>
        )}
      </div>

      {/* Create Category Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          resetForm();
        }}
        title="Create New Category"
      >
        {renderCategoryForm()}
        <div className="flex justify-end space-x-3 pt-4">
          <Button
            variant="outline"
            onClick={() => {
              setIsCreateModalOpen(false);
              resetForm();
            }}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleCreate} disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Category'}
          </Button>
        </div>
      </Modal>

      {/* Edit Category Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingCategory(null);
          resetForm();
        }}
        title="Edit Category"
      >
        {renderCategoryForm()}
        <div className="flex justify-end space-x-3 pt-4">
          <Button
            variant="outline"
            onClick={() => {
              setIsEditModalOpen(false);
              setEditingCategory(null);
              resetForm();
            }}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button onClick={handleEdit} disabled={isSubmitting}>
            {isSubmitting ? 'Updating...' : 'Update Category'}
          </Button>
        </div>
      </Modal>

      {/* Delete Category Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => {
          setIsDeleteModalOpen(false);
          setDeletingCategory(null);
        }}
        title="Delete Category"
      >
        <p className="mb-4 text-[hsl(var(--text))] opacity-80">
          Are you sure you want to delete "{deletingCategory?.name}"? This action cannot be undone.
        </p>
        <div className="flex justify-end space-x-3">
          <Button
            variant="outline"
            onClick={() => {
              setIsDeleteModalOpen(false);
              setDeletingCategory(null);
            }}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            disabled={isSubmitting}
            className="bg-red-600 hover:bg-red-700"
          >
            {isSubmitting ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}