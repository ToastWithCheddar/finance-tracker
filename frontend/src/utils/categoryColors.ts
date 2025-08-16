// Category color mapping for consistent UI theming
export const getCategoryColor = (categoryName: string | null | undefined): {
  bgColor: string;
  textColor: string;
  borderColor: string;
  badgeClass: string;
} => {
  if (!categoryName) {
    return {
      bgColor: 'bg-gray-100 dark:bg-gray-800',
      textColor: 'text-gray-800 dark:text-gray-100',
      borderColor: 'border-gray-200 dark:border-gray-700',
      badgeClass: 'bg-gray-100 text-gray-800 border border-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:border-gray-700'
    };
  }

  const category = categoryName.toLowerCase();
  
  // Food & Dining
  if (category.includes('food') || category.includes('restaurant') || category.includes('dining') || 
      category.includes('grocery') || category.includes('cafe') || category.includes('coffee')) {
    return {
      bgColor: 'bg-food-100 dark:bg-food-800',
      textColor: 'text-food-800 dark:text-food-100',
      borderColor: 'border-food-200 dark:border-food-700',
      badgeClass: 'badge-food'
    };
  }
  
  // Transportation
  if (category.includes('transport') || category.includes('gas') || category.includes('fuel') ||
      category.includes('car') || category.includes('uber') || category.includes('taxi') ||
      category.includes('train') || category.includes('bus') || category.includes('parking')) {
    return {
      bgColor: 'bg-transport-100 dark:bg-transport-800',
      textColor: 'text-transport-800 dark:text-transport-100',
      borderColor: 'border-transport-200 dark:border-transport-700',
      badgeClass: 'badge-transport'
    };
  }
  
  // Entertainment
  if (category.includes('entertainment') || category.includes('movie') || category.includes('music') ||
      category.includes('game') || category.includes('streaming') || category.includes('netflix') ||
      category.includes('spotify') || category.includes('concert') || category.includes('hobby')) {
    return {
      bgColor: 'bg-entertainment-100 dark:bg-entertainment-800',
      textColor: 'text-entertainment-800 dark:text-entertainment-100',
      borderColor: 'border-entertainment-200 dark:border-entertainment-700',
      badgeClass: 'badge-entertainment'
    };
  }
  
  // Shopping
  if (category.includes('shopping') || category.includes('retail') || category.includes('amazon') ||
      category.includes('store') || category.includes('clothes') || category.includes('clothing') ||
      category.includes('fashion') || category.includes('electronics')) {
    return {
      bgColor: 'bg-shopping-100 dark:bg-shopping-800',
      textColor: 'text-shopping-800 dark:text-shopping-100',
      borderColor: 'border-shopping-200 dark:border-shopping-700',
      badgeClass: 'badge-shopping'
    };
  }
  
  // Health
  if (category.includes('health') || category.includes('medical') || category.includes('doctor') ||
      category.includes('pharmacy') || category.includes('hospital') || category.includes('fitness') ||
      category.includes('gym') || category.includes('wellness')) {
    return {
      bgColor: 'bg-health-100 dark:bg-health-800',
      textColor: 'text-health-800 dark:text-health-100',
      borderColor: 'border-health-200 dark:border-health-700',
      badgeClass: 'badge-health'
    };
  }
  
  // Education
  if (category.includes('education') || category.includes('school') || category.includes('course') ||
      category.includes('book') || category.includes('learning') || category.includes('tuition')) {
    return {
      bgColor: 'bg-education-100 dark:bg-education-800',
      textColor: 'text-education-800 dark:text-education-100',
      borderColor: 'border-education-200 dark:border-education-700',
      badgeClass: 'badge-education'
    };
  }
  
  // Income
  if (category.includes('salary') || category.includes('income') || category.includes('paycheck') ||
      category.includes('bonus') || category.includes('refund') || category.includes('cashback')) {
    return {
      bgColor: 'bg-income-100 dark:bg-income-800',
      textColor: 'text-income-800 dark:text-income-100',
      borderColor: 'border-income-200 dark:border-income-700',
      badgeClass: 'bg-income-100 text-income-800 border border-income-200 dark:bg-income-800 dark:text-income-100 dark:border-income-700'
    };
  }
  
  // Savings & Investment
  if (category.includes('saving') || category.includes('investment') || category.includes('deposit') ||
      category.includes('retirement') || category.includes('401k') || category.includes('stock')) {
    return {
      bgColor: 'bg-investment-100 dark:bg-investment-800',
      textColor: 'text-investment-800 dark:text-investment-100',
      borderColor: 'border-investment-200 dark:border-investment-700',
      badgeClass: 'bg-investment-100 text-investment-800 border border-investment-200 dark:bg-investment-800 dark:text-investment-100 dark:border-investment-700'
    };
  }
  
  // Bills & Utilities
  if (category.includes('bill') || category.includes('utility') || category.includes('electric') ||
      category.includes('water') || category.includes('internet') || category.includes('phone') ||
      category.includes('rent') || category.includes('mortgage') || category.includes('insurance')) {
    return {
      bgColor: 'bg-budget-100 dark:bg-budget-800',
      textColor: 'text-budget-800 dark:text-budget-100',
      borderColor: 'border-budget-200 dark:border-budget-700',
      badgeClass: 'bg-budget-100 text-budget-800 border border-budget-200 dark:bg-budget-800 dark:text-budget-100 dark:border-budget-700'
    };
  }
  
  // Default fallback with a nice purple theme
  return {
    bgColor: 'bg-purple-100 dark:bg-purple-800',
    textColor: 'text-purple-800 dark:text-purple-100',
    borderColor: 'border-purple-200 dark:border-purple-700',
    badgeClass: 'bg-purple-100 text-purple-800 border border-purple-200 dark:bg-purple-800 dark:text-purple-100 dark:border-purple-700'
  };
};

// Get transaction amount color (income vs expense)
export const getAmountColor = (amount: number): {
  textColor: string;
  bgColor: string;
} => {
  if (amount > 0) {
    return {
      textColor: 'text-income-600 dark:text-income-400',
      bgColor: 'bg-income-50 dark:bg-income-900/20'
    };
  } else {
    return {
      textColor: 'text-expense-600 dark:text-expense-400',
      bgColor: 'bg-expense-50 dark:bg-expense-900/20'
    };
  }
};