import React, { useState } from 'react';
import { 
  Copy, 
  Star, 
  Download, 
  Filter,
  Search,
  Tag,
  Settings,
  TrendingUp
} from 'lucide-react';
import { Button } from '../ui/Button';
import { useCategorizationRuleActions } from '../../hooks/useCategorizationRules';
import type { CategorizationRuleTemplate } from '../../types/categorizationRules';

interface RuleTemplateGalleryProps {
  templates: CategorizationRuleTemplate[];
}

interface TemplateCardProps {
  template: CategorizationRuleTemplate;
  onCreateFromTemplate: (templateId: string) => void;
  isLoading: boolean;
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onCreateFromTemplate,
  isLoading
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getCategoryColor = (category: string) => {
    const colors = {
      'Dining': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
      'Shopping': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100',
      'Transportation': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100',
      'Entertainment': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100',
      'Healthcare': 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-100',
      'Utilities': 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100',
      'Finance': 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-100',
    };
    return colors[category as keyof typeof colors] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100';
  };

  return (
    <div className="bg-[hsl(var(--surface))] border border-[hsl(var(--border))] rounded-lg p-6 hover:shadow-md transition-all duration-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="text-lg font-semibold text-[hsl(var(--text))]">{template.name}</h3>
            {template.is_official && (
              <span className="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100">
                Official
              </span>
            )}
          </div>
          <p className="text-sm text-[hsl(var(--text))] opacity-70 mb-3">
            {template.description}
          </p>
          <div className="flex items-center space-x-2">
            <span className={`px-2 py-1 text-xs font-medium rounded ${getCategoryColor(template.category)}`}>
              <Tag className="h-3 w-3 inline mr-1" />
              {template.category}
            </span>
            <span className="px-2 py-1 text-xs font-medium rounded bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100">
              <TrendingUp className="h-3 w-3 inline mr-1" />
              {template.popularity_score} uses
            </span>
          </div>
        </div>
        
        <div className="flex flex-col space-y-2">
          <Button
            size="sm"
            onClick={() => onCreateFromTemplate(template.id)}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Copy className="h-4 w-4 mr-2" />
            Use Template
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setShowDetails(!showDetails)}
          >
            <Settings className="h-4 w-4 mr-2" />
            Details
          </Button>
        </div>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="border-t border-[hsl(var(--border))] pt-4 mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Condition Template</h4>
              <div className="bg-[hsl(var(--bg))] p-3 rounded-lg">
                <pre className="text-xs text-[hsl(var(--text))] whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(template.conditions_template, null, 2)}
                </pre>
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-[hsl(var(--text))] mb-2">Action Template</h4>
              <div className="bg-[hsl(var(--bg))] p-3 rounded-lg">
                <pre className="text-xs text-[hsl(var(--text))] whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(template.actions_template, null, 2)}
                </pre>
              </div>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-[hsl(var(--border))]">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-lg font-bold text-[hsl(var(--text))]">{template.default_priority}</p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Default Priority</p>
              </div>
              <div>
                <p className="text-lg font-bold text-[hsl(var(--text))]">{template.popularity_score}</p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Popularity</p>
              </div>
              <div>
                <p className="text-lg font-bold text-[hsl(var(--text))]">
                  {template.is_official ? 'Yes' : 'No'}
                </p>
                <p className="text-xs text-[hsl(var(--text))] opacity-70">Official</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const RuleTemplateGallery: React.FC<RuleTemplateGalleryProps> = ({ templates }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [showOfficialOnly, setShowOfficialOnly] = useState(false);
  
  const actions = useCategorizationRuleActions();

  // Get unique categories
  const categories = Array.from(new Set(templates.map(t => t.category))).sort();

  // Filter templates
  const filteredTemplates = templates.filter(template => {
    const matchesSearch = !searchTerm || 
      template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      template.description.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = !selectedCategory || template.category === selectedCategory;
    const matchesOfficial = !showOfficialOnly || template.is_official;
    
    return matchesSearch && matchesCategory && matchesOfficial;
  });

  // Sort by popularity
  const sortedTemplates = filteredTemplates.sort((a, b) => b.popularity_score - a.popularity_score);

  /**
   * Creates a new categorization rule from a template
   * @param templateId - ID of the template to use as base
   * 
   * TODO: Implement template customization modal
   * Implementation should:
   * 1. Open a modal/form component (e.g., RuleFromTemplateModal)
   * 2. Pre-populate form with template's conditions and actions
   * 3. Allow user to customize:
   *    - Rule name (default: "New Rule from {template.name}")
   *    - Target category (required - show category selector)
   *    - Condition values (e.g., merchant names, amount ranges)
   *    - Rule priority/order
   * 4. Validate required fields before submission
   * 5. Call createFromTemplate mutation with user customizations
   * 6. Show success/error toast and close modal on completion
   */
  const handleCreateFromTemplate = (templateId: string) => {
    console.log('Create rule from template:', templateId);
    
    // For now, use default customizations
    const defaultCustomizations = {
      name: `New Rule from Template`,
      // target_category_id would be selected by user
    };
    
    actions.createFromTemplate.mutate({
      templateId,
      customizations: defaultCustomizations
    });
  };

  return (
    <div className="space-y-6">
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[hsl(var(--text))] opacity-50" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface))] text-[hsl(var(--text))] placeholder-[hsl(var(--text))/0.5] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent"
          />
        </div>
        
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="px-4 py-2 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface))] text-[hsl(var(--text))] focus:ring-2 focus:ring-[hsl(var(--brand))] focus:border-transparent"
        >
          <option value="">All Categories</option>
          {categories.map(category => (
            <option key={category} value={category}>{category}</option>
          ))}
        </select>
        
        <label className="flex items-center space-x-2 text-sm">
          <input
            type="checkbox"
            checked={showOfficialOnly}
            onChange={(e) => setShowOfficialOnly(e.target.checked)}
            className="rounded"
          />
          <span className="text-[hsl(var(--text))]">Official only</span>
        </label>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {sortedTemplates.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            onCreateFromTemplate={handleCreateFromTemplate}
            isLoading={actions.isLoading}
          />
        ))}
      </div>

      {/* No Results */}
      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <Copy className="h-12 w-12 mx-auto mb-4 text-[hsl(var(--text))] opacity-30" />
          <p className="text-[hsl(var(--text))] opacity-80">
            {searchTerm || selectedCategory || showOfficialOnly
              ? 'No templates match your filters.'
              : 'No templates available.'
            }
          </p>
          <p className="text-sm text-[hsl(var(--text))] opacity-70">
            {searchTerm || selectedCategory || showOfficialOnly
              ? 'Try adjusting your search or filters.'
              : 'Check back later for new templates.'
            }
          </p>
        </div>
      )}

      {/* Template Stats */}
      <div className="bg-[hsl(var(--surface))] p-4 rounded-lg border border-[hsl(var(--border))]">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-[hsl(var(--text))]">{templates.length}</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Total Templates</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-[hsl(var(--text))]">
              {templates.filter(t => t.is_official).length}
            </p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Official</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-[hsl(var(--text))]">{categories.length}</p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Categories</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-[hsl(var(--text))]">
              {Math.round(templates.reduce((sum, t) => sum + t.popularity_score, 0) / templates.length)}
            </p>
            <p className="text-sm text-[hsl(var(--text))] opacity-70">Avg. Popularity</p>
          </div>
        </div>
      </div>
    </div>
  );
};