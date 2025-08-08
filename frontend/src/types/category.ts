export interface Category {
  id: string;
  user_id?: string;
  name: string;
  description?: string;
  emoji?: string;
  color?: string;
  icon?: string;
  parent_id?: string;
  is_system: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCategoryRequest {
  name: string;
  description?: string;
  emoji?: string;
  color?: string;
  icon?: string;
  parent_id?: string;
  [key: string]: unknown;
}

export interface UpdateCategoryRequest extends Partial<CreateCategoryRequest> {
  is_active?: boolean;
  sort_order?: number;
}

export interface CategoryWithChildren extends Category {
  children: CategoryWithChildren[];
}

export interface CategoryStats {
  transaction_count: number;
  total_amount_cents: number;
}