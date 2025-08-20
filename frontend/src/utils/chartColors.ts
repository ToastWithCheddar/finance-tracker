// Centralized color palette for charts and data visualization
// This ensures consistency across all chart components

export const CHART_COLORS = [
  '#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8',
  '#82CA9D', '#FFC658', '#FF7C7C', '#8DD1E1', '#D084D0'
];

// Standard colors for specific chart types
export const CHART_THEME = {
  // Income/Expense colors for financial charts
  income: '#10B981',
  expenses: '#EF4444',
  
  // Status colors
  success: '#10B981',
  warning: '#F59E0B',
  danger: '#EF4444',
  info: '#3B82F6',
  
  // Goal priority colors (for future use)
  priority: {
    high: '#EF4444',
    medium: '#F59E0B',
    low: '#10B981'
  }
} as const;

// Nivo chart specific theme configuration
export const NIVO_CHART_THEME = {
  background: 'transparent',
  text: {
    fontSize: 12,
    fill: '#374151',
    outlineWidth: 0,
    outlineColor: 'transparent',
  },
  axis: {
    domain: {
      line: {
        stroke: '#e5e7eb',
        strokeWidth: 1,
      },
    },
    legend: {
      text: {
        fontSize: 12,
        fill: '#374151',
      },
    },
    ticks: {
      line: {
        stroke: '#e5e7eb',
        strokeWidth: 1,
      },
      text: {
        fontSize: 11,
        fill: '#6b7280',
      },
    },
  },
  grid: {
    line: {
      stroke: '#f3f4f6',
      strokeWidth: 1,
    },
  },
  legends: {
    title: {
      text: {
        fontSize: 11,
        fill: '#374151',
      },
    },
    text: {
      fontSize: 11,
      fill: '#374151',
    },
    ticks: {
      line: {},
      text: {
        fontSize: 10,
        fill: '#374151',
      },
    },
  },
  annotations: {
    text: {
      fontSize: 13,
      fill: '#374151',
      outlineWidth: 2,
      outlineColor: '#ffffff',
      outlineOpacity: 1,
    },
    link: {
      stroke: '#000000',
      strokeWidth: 1,
      outlineWidth: 2,
      outlineColor: '#ffffff',
      outlineOpacity: 1,
    },
    outline: {
      stroke: '#000000',
      strokeWidth: 2,
      outlineWidth: 2,
      outlineColor: '#ffffff',
      outlineOpacity: 1,
    },
    symbol: {
      fill: '#000000',
      outlineWidth: 2,
      outlineColor: '#ffffff',
      outlineOpacity: 1,
    },
  },
  tooltip: {
    container: {
      background: 'transparent',
      border: 'none',
      boxShadow: 'none',
    },
  },
} as const;

// Dark theme variant for Nivo charts
export const NIVO_CHART_THEME_DARK = {
  ...NIVO_CHART_THEME,
  text: {
    ...NIVO_CHART_THEME.text,
    fill: '#f3f4f6',
  },
  axis: {
    ...NIVO_CHART_THEME.axis,
    domain: {
      line: {
        stroke: '#4b5563',
        strokeWidth: 1,
      },
    },
    legend: {
      text: {
        fontSize: 12,
        fill: '#f3f4f6',
      },
    },
    ticks: {
      line: {
        stroke: '#4b5563',
        strokeWidth: 1,
      },
      text: {
        fontSize: 11,
        fill: '#9ca3af',
      },
    },
  },
  grid: {
    line: {
      stroke: '#374151',
      strokeWidth: 1,
    },
  },
  legends: {
    title: {
      text: {
        fontSize: 11,
        fill: '#f3f4f6',
      },
    },
    text: {
      fontSize: 11,
      fill: '#f3f4f6',
    },
    ticks: {
      line: {},
      text: {
        fontSize: 10,
        fill: '#f3f4f6',
      },
    },
  },
  annotations: {
    text: {
      fontSize: 13,
      fill: '#f3f4f6',
      outlineWidth: 2,
      outlineColor: '#1f2937',
      outlineOpacity: 1,
    },
    link: {
      stroke: '#f3f4f6',
      strokeWidth: 1,
      outlineWidth: 2,
      outlineColor: '#1f2937',
      outlineOpacity: 1,
    },
    outline: {
      stroke: '#f3f4f6',
      strokeWidth: 2,
      outlineWidth: 2,
      outlineColor: '#1f2937',
      outlineOpacity: 1,
    },
    symbol: {
      fill: '#f3f4f6',
      outlineWidth: 2,
      outlineColor: '#1f2937',
      outlineOpacity: 1,
    },
  },
} as const;

// Helper function to get a color by index (cycling through the palette)
export const getChartColor = (index: number): string => {
  return CHART_COLORS[index % CHART_COLORS.length];
};