import { LayoutDashboard, ReceiptText, Tags, Wallet, Target } from 'lucide-react';

export interface NavigationItem {
  path: string;
  label: string;
  icon: any;
  description: string;
  color?: string;
  hoverColor?: string;
}

export const navigationItems: NavigationItem[] = [
  { 
    path: '/dashboard', 
    label: 'Dashboard', 
    icon: LayoutDashboard, 
    description: 'Overview of balances, trends, and live updates', 
    color: 'text-blue-600 dark:text-blue-400', 
    hoverColor: 'hover:bg-blue-50 dark:hover:bg-blue-900/30' 
  },
  { 
    path: '/transactions', 
    label: 'Transactions', 
    icon: ReceiptText, 
    description: 'Browse and manage your transactions', 
    color: 'text-green-600 dark:text-green-400', 
    hoverColor: 'hover:bg-green-50 dark:hover:bg-green-900/30' 
  },
  { 
    path: '/categories', 
    label: 'Categories', 
    icon: Tags, 
    description: 'Organize and maintain your spending categories', 
    color: 'text-orange-600 dark:text-orange-400', 
    hoverColor: 'hover:bg-orange-50 dark:hover:bg-orange-900/30' 
  },
  { 
    path: '/budgets', 
    label: 'Budgets', 
    icon: Wallet, 
    description: 'Create budgets and track progress', 
    color: 'text-red-600 dark:text-red-400', 
    hoverColor: 'hover:bg-red-50 dark:hover:bg-red-900/30' 
  },
  { 
    path: '/goals', 
    label: 'Goals', 
    icon: Target, 
    description: 'Plan and monitor financial goals', 
    color: 'text-yellow-600 dark:text-yellow-400', 
    hoverColor: 'hover:bg-yellow-50 dark:hover:bg-yellow-900/30' 
  },
];