import { create } from 'zustand';

interface GlobalFiltersState {
  start_date?: string;
  end_date?: string;
  setDateRange: (start?: string, end?: string) => void;
  clear: () => void;
}

export const useGlobalFilters = create<GlobalFiltersState>((set) => ({
  start_date: undefined,
  end_date: undefined,
  setDateRange: (start, end) => set({ start_date: start, end_date: end }),
  clear: () => set({ start_date: undefined, end_date: undefined }),
}));


