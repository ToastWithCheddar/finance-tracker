# Import Organization Standards

## Python Import Order

Follow this order for all Python files:

1. **Standard library imports** (alphabetical)
2. **Third-party imports** (alphabetical)
3. **Local application imports** (alphabetical)

Within each section, use alphabetical ordering.

## Example Structure

```python
# Standard library imports
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import relationship, mapped_column, Mapped

# Local application imports
from ..auth.dependencies import get_current_user
from ..core.exceptions import ResourceNotFoundException
from ..database import get_db
from ..models.user import User
from ..schemas.base import BaseResponseSchema
```

## Specific Guidelines

### Models
```python
# Standard library
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

# Third-party
from sqlalchemy import String, Integer, Boolean, Date, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship, mapped_column, Mapped

# Local
from .base import BaseModel
```

### Schemas
```python
# Standard library
from datetime import datetime
from typing import Optional, List
from uuid import UUID

# Third-party
from pydantic import BaseModel, Field, validator

# Local
from .base import BaseResponseSchema
```

### Services
```python
# Standard library
import logging
from typing import Optional, List
from uuid import UUID

# Third-party
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

# Local
from ..core.exceptions import ResourceNotFoundException
from ..models.transaction import Transaction
from ..schemas.transaction import TransactionCreate
```

### Routes
```python
# Standard library
from typing import List, Optional
from uuid import UUID

# Third-party
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

# Local
from ..auth.dependencies import get_current_user
from ..database import get_db
from ..models.user import User
from ..schemas.transaction import TransactionResponse
from ..services.transaction_service import TransactionService
```

## Tools for Enforcement

Use `isort` with this configuration in `pyproject.toml`:

```toml
[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88
known_first_party = ["app"]
known_third_party = ["fastapi", "pydantic", "sqlalchemy"]
sections = ["FUTURE", "STDLIB", "THIRDPARTY", "FIRSTPARTY", "LOCALFOLDER"]
```

## Frontend Import Standards

### TypeScript/React Import Order

1. **React and React ecosystem**
2. **Third-party libraries**
3. **Internal utilities and services**
4. **Components** (from most general to most specific)
5. **Types and interfaces**
6. **Relative imports**

```typescript
// React ecosystem
import React, { useState, useEffect } from 'react';
import { create } from 'zustand';

// Third-party libraries
import axios from 'axios';
import { format } from 'date-fns';

// Internal utilities and services
import { apiClient } from '@/services/api';
import { formatCurrency } from '@/utils/currency';

// Components
import { Button } from '@/components/ui/Button';
import { TransactionCard } from '@/components/transactions/TransactionCard';

// Types
import type { Transaction } from '@/types/transaction';
import type { ApiResponse } from '@/types/api';

// Relative imports
import './TransactionList.css';
```