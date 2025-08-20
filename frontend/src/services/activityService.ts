import { apiClient } from './api';
import type { ActivityEvent, ActivityFeedOptions, ActivityResponse } from '../types/activity';

export class ActivityService {
  /**
   * Get user activity feed from the backend
   */
  async getActivityFeed(options: ActivityFeedOptions = {}): Promise<ActivityResponse> {
    const params = new URLSearchParams();
    
    if (options.limit) {
      params.append('limit', options.limit.toString());
    }
    if (options.table_name) {
      params.append('table_name', options.table_name);
    }
    if (options.since) {
      params.append('since', options.since);
    }

    const queryString = params.toString();
    const url = `/users/me/activity${queryString ? `?${queryString}` : ''}`;
    
    return apiClient.get<ActivityResponse>(url);
  }

  /**
   * Get activities from audit logs (fallback method)
   */
  async getAuditBasedActivities(options: ActivityFeedOptions = {}): Promise<ActivityEvent[]> {
    const params = new URLSearchParams();
    
    if (options.limit) {
      params.append('limit', options.limit.toString());
    }
    if (options.table_name) {
      params.append('table_name', options.table_name);
    }

    const queryString = params.toString();
    const url = `/audit/recent${queryString ? `?${queryString}` : ''}`;
    
    // Transform audit logs to activity events
    const auditLogs = await apiClient.get<any[]>(url);
    
    return auditLogs.map(log => this.transformAuditLogToActivity(log));
  }

  /**
   * Transform audit log entry to activity event
   */
  private transformAuditLogToActivity(auditLog: any): ActivityEvent {
    const { id, table_name, action, old_data, new_data, created_at, row_id } = auditLog;
    
    // Determine activity type based on table and action
    const activityType = this.getActivityTypeFromAudit(table_name, action);
    
    // Generate title and description
    const { title, description } = this.generateActivityTitleAndDescription(
      table_name, 
      action, 
      old_data, 
      new_data
    );

    return {
      id,
      type: activityType,
      title,
      description,
      timestamp: created_at,
      table_name,
      record_id: row_id,
      metadata: {
        action,
        old_data,
        new_data,
      },
    };
  }

  /**
   * Map audit table/action to activity type
   */
  private getActivityTypeFromAudit(tableName: string, action: string): string {
    const mapping: Record<string, Record<string, string>> = {
      transactions: {
        INSERT: 'transaction_created',
        UPDATE: 'transaction_updated',
        DELETE: 'transaction_deleted',
      },
      budgets: {
        INSERT: 'budget_created',
        UPDATE: 'budget_updated',
        DELETE: 'budget_deleted',
      },
      goals: {
        INSERT: 'goal_created',
        UPDATE: 'goal_updated',
        DELETE: 'goal_deleted',
      },
      accounts: {
        INSERT: 'account_connected',
        UPDATE: 'account_updated',
      },
      categories: {
        INSERT: 'category_created',
        UPDATE: 'category_updated',
        DELETE: 'category_deleted',
      },
      categorization_rules: {
        INSERT: 'rule_created',
        UPDATE: 'rule_updated',
        DELETE: 'rule_deleted',
      },
    };

    return mapping[tableName]?.[action] || 'settings_updated';
  }

  /**
   * Generate human-readable title and description from audit data
   */
  private generateActivityTitleAndDescription(
    tableName: string, 
    action: string, 
    oldData: any, 
    newData: any
  ): { title: string; description: string } {
    const data = newData || oldData || {};
    const entityName = data.name || data.description || data.title || 'Item';

    switch (tableName) {
      case 'transactions':
        switch (action) {
          case 'INSERT':
            return {
              title: 'Transaction Created',
              description: `Created transaction: ${data.description || 'New transaction'}`,
            };
          case 'UPDATE':
            return {
              title: 'Transaction Updated',
              description: `Updated transaction: ${data.description || 'Transaction modified'}`,
            };
          case 'DELETE':
            return {
              title: 'Transaction Deleted',
              description: `Deleted transaction: ${oldData?.description || 'Transaction removed'}`,
            };
        }
        break;

      case 'budgets':
        switch (action) {
          case 'INSERT':
            return {
              title: 'Budget Created',
              description: `Created budget: ${entityName}`,
            };
          case 'UPDATE':
            return {
              title: 'Budget Updated',
              description: `Updated budget: ${entityName}`,
            };
          case 'DELETE':
            return {
              title: 'Budget Deleted',
              description: `Deleted budget: ${oldData?.name || 'Budget removed'}`,
            };
        }
        break;

      case 'goals':
        switch (action) {
          case 'INSERT':
            return {
              title: 'Goal Created',
              description: `Created goal: ${entityName}`,
            };
          case 'UPDATE':
            return {
              title: 'Goal Updated',
              description: `Updated goal: ${entityName}`,
            };
          case 'DELETE':
            return {
              title: 'Goal Deleted',
              description: `Deleted goal: ${oldData?.name || 'Goal removed'}`,
            };
        }
        break;

      case 'accounts':
        switch (action) {
          case 'INSERT':
            return {
              title: 'Account Connected',
              description: `Connected account: ${entityName}`,
            };
          case 'UPDATE':
            return {
              title: 'Account Updated',
              description: `Updated account: ${entityName}`,
            };
        }
        break;

      case 'categories':
        switch (action) {
          case 'INSERT':
            return {
              title: 'Category Created',
              description: `Created category: ${entityName}`,
            };
          case 'UPDATE':
            return {
              title: 'Category Updated',
              description: `Updated category: ${entityName}`,
            };
          case 'DELETE':
            return {
              title: 'Category Deleted',
              description: `Deleted category: ${oldData?.name || 'Category removed'}`,
            };
        }
        break;

      default:
        return {
          title: 'Data Updated',
          description: `${action.toLowerCase()} operation on ${tableName}`,
        };
    }

    return {
      title: 'Activity',
      description: `${action} on ${tableName}`,
    };
  }
}

// Export singleton instance
export const activityService = new ActivityService();