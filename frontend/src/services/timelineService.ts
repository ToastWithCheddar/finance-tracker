import { BaseService } from './base/BaseService';
import { apiClient } from './api';

// Timeline annotation types
export interface TimelineAnnotation {
  id: string;
  user_id: string;
  date: string;
  title: string;
  description?: string;
  icon?: string;
  color?: string;
  extra_data?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export interface TimelineAnnotationCreate {
  date: string;
  title: string;
  description?: string;
  icon?: string;
  color?: string;
  extra_data?: Record<string, any>;
  [key: string]: unknown;
}

export interface TimelineAnnotationUpdate {
  date?: string;
  title?: string;
  description?: string;
  icon?: string;
  color?: string;
  extra_data?: Record<string, any>;
  [key: string]: unknown;
}

export interface TimelineEvent {
  id: string;
  date: string;
  type: string;
  title: string;
  description?: string;
  icon: string;
  color: string;
  source: string;
  extra_data?: Record<string, any>;
  created_at?: string;
}

export interface TimelineEventsList {
  events: TimelineEvent[];
  total_count: number;
  start_date: string;
  end_date: string;
}

export interface TimelineAnnotationsList {
  annotations: TimelineAnnotation[];
  total_count: number;
  page: number;
  limit: number;
}

export interface TimelineFilters {
  page?: number;
  limit?: number;
  start_date?: string;
  end_date?: string;
}

class TimelineService extends BaseService {
  protected baseEndpoint = '/annotations';

  // Timeline Annotations CRUD Operations
  async createAnnotation(data: TimelineAnnotationCreate): Promise<TimelineAnnotation> {
    return this.post<TimelineAnnotation>('/', data);
  }

  async getAnnotations(filters?: TimelineFilters): Promise<TimelineAnnotationsList> {
    const params = this.buildParams(filters || {});
    return this.get<TimelineAnnotationsList>('/', params);
  }

  async getAnnotation(id: string): Promise<TimelineAnnotation> {
    return this.get<TimelineAnnotation>(`/${id}`);
  }

  async updateAnnotation(id: string, data: TimelineAnnotationUpdate): Promise<TimelineAnnotation> {
    return this.put<TimelineAnnotation>(`/${id}`, data);
  }

  async deleteAnnotation(id: string): Promise<void> {
    return this.delete(`/${id}`);
  }

  // Financial Timeline Aggregation
  async getFinancialTimeline(startDate: string, endDate: string): Promise<TimelineEventsList> {
    const params = {
      start_date: startDate,
      end_date: endDate,
    };

    // Call analytics endpoint directly to avoid baseEndpoint prefix
    return apiClient.get<TimelineEventsList>('/analytics/timeline', params);
  }
}

export const timelineService = new TimelineService();