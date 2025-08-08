import { useState, useEffect, useMemo, useCallback } from 'react';
import { ChevronDownIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { categoryService } from '../../services/categoryService';
import type { Category, CategoryWithChildren } from '../../types/category';

interface CategorySelectorProps {
  value?: string;
  onChange: (categoryId: string | undefined, category: Category | undefined) => void;
  transactionType?: 'income' | 'expense';
  placeholder?: string;
  error?: string;
  required?: boolean;
  className?: string;
}

export function CategorySelector({
  value,
  onChange,
  transactionType,
  placeholder = "Select a category",
  error,
  required = false,
  className = ''
}: CategorySelectorProps) {
  const [categories, setCategories] = useState<CategoryWithChildren[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<Category | undefined>();

  const loadCategories = useCallback(async () => {
    try {
      setLoading(true);
      let categoryList: Category[];
      
      if (transactionType) {
        categoryList = await categoryService.getCategoriesForTransactionType(transactionType);
      } else {
        categoryList = await categoryService.getMyCategories();
      }
      
      // Build hierarchy
      const hierarchy = buildHierarchy(categoryList);
      setCategories(hierarchy);
    } catch (error) {
      console.error('Failed to load categories:', error);
    } finally {
      setLoading(false);
    }
  }, [transactionType]);

  useEffect(() => {
    loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    if (value && categories.length > 0) {
      findCategoryById(value);
    } else {
      setSelectedCategory(undefined);
    }
  }, [value, categories]);

  const findCategoryById = async (categoryId: string) => {
    try {
      const category = await categoryService.getCategory(categoryId);
      setSelectedCategory(category);
    } catch (error) {
      console.error('Failed to find category:', error);
      setSelectedCategory(undefined);
    }
  };

  const buildHierarchy = (categoryList: Category[]): CategoryWithChildren[] => {
    const categoryMap = new Map<string, CategoryWithChildren>();
    const rootCategories: CategoryWithChildren[] = [];

    // First pass: create all category objects
    categoryList.forEach(cat => {
      categoryMap.set(cat.id, { ...cat, children: [] });
    });

    // Second pass: build hierarchy
    categoryList.forEach(cat => {
      const categoryWithChildren = categoryMap.get(cat.id)!;
      
      if (cat.parent_id) {
        const parent = categoryMap.get(cat.parent_id);
        if (parent) {
          parent.children.push(categoryWithChildren);
        }
      } else {
        rootCategories.push(categoryWithChildren);
      }
    });

    // Sort categories
    const sortCategories = (cats: CategoryWithChildren[]) => {
      cats.sort((a, b) => {
        if (a.sort_order !== b.sort_order) {
          return a.sort_order - b.sort_order;
        }
        return a.name.localeCompare(b.name);
      });
      cats.forEach(cat => sortCategories(cat.children));
    };

    sortCategories(rootCategories);
    return rootCategories;
  };

  const filteredCategories = useMemo(() => {
    if (!searchTerm) return categories;

    const filterCategories = (cats: CategoryWithChildren[]): CategoryWithChildren[] => {
      return cats.reduce((acc: CategoryWithChildren[], cat) => {
        const matchesSearch = cat.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                            cat.description?.toLowerCase().includes(searchTerm.toLowerCase());
        
        const filteredChildren = filterCategories(cat.children);
        
        if (matchesSearch || filteredChildren.length > 0) {
          acc.push({
            ...cat,
            children: filteredChildren
          });
        }
        
        return acc;
      }, []);
    };

    return filterCategories(categories);
  }, [categories, searchTerm]);

  const handleCategorySelect = (category: Category) => {
    setSelectedCategory(category);
    onChange(category.id, category);
    setIsOpen(false);
    setSearchTerm('');
  };

  const renderCategory = (category: CategoryWithChildren, level: number = 0) => {
    const paddingLeft = level * 20;
    
    return (
      <div key={category.id}>
        <button
          type="button"
          onClick={() => handleCategorySelect(category)}
          className={`w-full text-left px-3 py-2 hover:bg-gray-100 flex items-center ${
            value === category.id ? 'bg-blue-50 text-blue-700' : ''
          }`}
          style={{ paddingLeft: `${12 + paddingLeft}px` }}
        >
          {category.emoji && (
            <span className="mr-2 text-base">{category.emoji}</span>
          )}
          <span className="flex-1">{category.name}</span>
          {category.is_system && (
            <span className="text-xs text-gray-500 ml-2">System</span>
          )}
        </button>
        
        {/* Render children */}
        {category.children.map(child => renderCategory(child, level + 1))}
      </div>
    );
  };

  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-3 py-2 text-left bg-white border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
          error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''
        } ${!selectedCategory ? 'text-gray-500' : ''}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center flex-1 min-w-0">
            {selectedCategory ? (
              <>
                {selectedCategory.emoji && (
                  <span className="mr-2 text-base">{selectedCategory.emoji}</span>
                )}
                <span className="truncate">{selectedCategory.name}</span>
              </>
            ) : (
              <span className="text-gray-500">{placeholder}</span>
            )}
          </div>
          <ChevronDownIcon 
            className={`ml-2 h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-80 overflow-hidden">
          {/* Search */}
          <div className="p-3 border-b border-gray-200">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search categories..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
            </div>
          </div>

          {/* Categories list */}
          <div className="max-h-60 overflow-y-auto">
            {loading ? (
              <div className="p-3 text-center text-gray-500">Loading categories...</div>
            ) : filteredCategories.length === 0 ? (
              <div className="p-3 text-center text-gray-500">
                {searchTerm ? 'No categories found' : 'No categories available'}
              </div>
            ) : (
              <>
                {/* Clear selection option */}
                {!required && (
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedCategory(undefined);
                      onChange(undefined, undefined);
                      setIsOpen(false);
                      setSearchTerm('');
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-gray-100 text-gray-500 border-b border-gray-100"
                  >
                    <span className="italic">No category</span>
                  </button>
                )}
                
                {/* Category list */}
                {filteredCategories.map(category => renderCategory(category))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => {
            setIsOpen(false);
            setSearchTerm('');
          }}
        />
      )}
    </div>
  );
}