/**
 * Activity feed types and interfaces for tracking user actions and system events
 */

export interface ActivityEvent {
  id: string;
  type: ActivityType;
  title: string;
  description: string;
  timestamp: string; // ISO timestamp
  icon?: string; // Lucide icon name
  metadata?: Record<string, any>;
  table_name?: string; // Source table from audit log
  record_id?: string; // Related record ID
  isNew?: boolean; // For real-time highlighting
}

export enum ActivityType {
  // Transaction activities
  TRANSACTION_CREATED = 'transaction_created',
  TRANSACTION_UPDATED = 'transaction_updated',
  TRANSACTION_DELETED = 'transaction_deleted',
  BULK_IMPORT = 'bulk_import',
  
  // Budget activities
  BUDGET_CREATED = 'budget_created',
  BUDGET_UPDATED = 'budget_updated',
  BUDGET_DELETED = 'budget_deleted',
  BUDGET_ALERT = 'budget_alert',
  
  // Goal activities
  GOAL_CREATED = 'goal_created',
  GOAL_UPDATED = 'goal_updated',
  GOAL_DELETED = 'goal_deleted',
  GOAL_ACHIEVED = 'goal_achieved',
  GOAL_MILESTONE = 'goal_milestone',
  
  // Account activities
  ACCOUNT_CONNECTED = 'account_connected',
  ACCOUNT_SYNCED = 'account_synced',
  ACCOUNT_UPDATED = 'account_updated',
  
  // Category activities
  CATEGORY_CREATED = 'category_created',
  CATEGORY_UPDATED = 'category_updated',
  CATEGORY_DELETED = 'category_deleted',
  
  // Automation activities
  RULE_CREATED = 'rule_created',
  RULE_UPDATED = 'rule_updated',
  RULE_APPLIED = 'rule_applied',
  
  // System activities
  SYNC_COMPLETED = 'sync_completed',
  EXPORT_GENERATED = 'export_generated',
  SETTINGS_UPDATED = 'settings_updated',
}

export interface ActivityFeedOptions {
  limit?: number;
  table_name?: string;
  since?: string; // ISO timestamp for filtering
}

export interface ActivityResponse {
  activities: ActivityEvent[];
  total_count: number;
  has_more: boolean;
}

// Icon mapping for different activity types
export const ACTIVITY_ICONS: Record<ActivityType, string> = {
  [ActivityType.TRANSACTION_CREATED]: 'plus-circle',
  [ActivityType.TRANSACTION_UPDATED]: 'edit-3',
  [ActivityType.TRANSACTION_DELETED]: 'trash-2',
  [ActivityType.BULK_IMPORT]: 'upload',
  
  [ActivityType.BUDGET_CREATED]: 'wallet',
  [ActivityType.BUDGET_UPDATED]: 'edit',
  [ActivityType.BUDGET_DELETED]: 'x-circle',
  [ActivityType.BUDGET_ALERT]: 'alert-triangle',
  
  [ActivityType.GOAL_CREATED]: 'target',
  [ActivityType.GOAL_UPDATED]: 'edit',
  [ActivityType.GOAL_DELETED]: 'x-circle',
  [ActivityType.GOAL_ACHIEVED]: 'trophy',
  [ActivityType.GOAL_MILESTONE]: 'flag',
  
  [ActivityType.ACCOUNT_CONNECTED]: 'link',
  [ActivityType.ACCOUNT_SYNCED]: 'refresh-cw',
  [ActivityType.ACCOUNT_UPDATED]: 'edit',
  
  [ActivityType.CATEGORY_CREATED]: 'tag',
  [ActivityType.CATEGORY_UPDATED]: 'edit',
  [ActivityType.CATEGORY_DELETED]: 'x-circle',
  
  [ActivityType.RULE_CREATED]: 'zap',
  [ActivityType.RULE_UPDATED]: 'edit',
  [ActivityType.RULE_APPLIED]: 'magic-wand',
  
  [ActivityType.SYNC_COMPLETED]: 'check-circle',
  [ActivityType.EXPORT_GENERATED]: 'download',
  [ActivityType.SETTINGS_UPDATED]: 'settings',
};

// Helper function to get icon for activity type
export function getActivityIcon(type: ActivityType): string {
  return ACTIVITY_ICONS[type] || 'activity';
}

// Helper function to format activity description
export function formatActivityDescription(activity: ActivityEvent): string {
  const { type, metadata = {} } = activity;
  
  switch (type) {
    case ActivityType.TRANSACTION_CREATED:
      return `Created transaction: ${metadata.description || 'New transaction'}`;
    case ActivityType.TRANSACTION_UPDATED:
      return `Updated transaction: ${metadata.description || 'Transaction updated'}`;
    case ActivityType.BULK_IMPORT:
      return `Imported ${metadata.count || 'multiple'} transactions`;
    case ActivityType.BUDGET_CREATED:
      return `Created budget: ${metadata.name || 'New budget'}`;
    case ActivityType.GOAL_ACHIEVED:
      return `🎉 Achieved goal: ${metadata.name || 'Goal completed'}`;
    case ActivityType.ACCOUNT_SYNCED:
      return `Synced account: ${metadata.account_name || 'Account updated'}`;
    default:
      return activity.description;
  }
}