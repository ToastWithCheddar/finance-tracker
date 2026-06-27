# Şekil 2 — Veri Modeli (Çekirdek Tablolar)

`backend/app/models/*.py` altındaki SQLAlchemy 2.0 modellerinden
türetilmiştir. Sadece çekirdek tablolar ve temsilî alanlar gösterilmiştir;
detay alanları (Plaid metadata, lokalizasyon vb.) sade kalsın diye
gizlenmiştir.

Para birimi için `amount_cents` BigInteger — kayan nokta kullanılmadığına
dikkat (kaynak: `transaction.py:23`).

```mermaid
erDiagram
    USERS ||--o{ ACCOUNTS : "owns"
    USERS ||--o{ TRANSACTIONS : "owns"
    USERS ||--o{ BUDGETS : "owns"
    USERS ||--o{ GOALS : "owns"
    USERS ||--o{ CATEGORIES : "custom"
    ACCOUNTS ||--o{ TRANSACTIONS : "contains"
    CATEGORIES ||--o{ TRANSACTIONS : "categorises"
    CATEGORIES ||--o{ BUDGETS : "scopes"
    CATEGORIES ||--o{ CATEGORIES : "parent"

    USERS {
      uuid id PK
      uuid supabase_user_id UK
      string email UK
      bool is_active
      bool is_admin
      string locale
      string currency
    }

    ACCOUNTS {
      uuid id PK
      uuid user_id FK
      string name
      string account_type
      bigint balance_cents
      string sync_status
      text plaid_access_token_encrypted
    }

    TRANSACTIONS {
      uuid id PK
      uuid user_id FK
      uuid account_id FK
      uuid category_id FK
      bigint amount_cents
      date transaction_date
      string status
      float confidence_score
      uuid ml_suggested_category_id FK
    }

    CATEGORIES {
      uuid id PK
      uuid user_id FK
      uuid parent_id FK
      string name
      bool is_system
    }

    BUDGETS {
      uuid id PK
      uuid user_id FK
      uuid category_id FK
      bigint amount_cents
      enum period
      date start_date
      float alert_threshold
    }

    GOALS {
      uuid id PK
      uuid user_id FK
      string name
      bigint target_cents
      enum goal_type
      enum priority
      enum status
    }
```

## Kanıt ve Çapraz Referanslar

- Tablo kaynakları: `backend/app/models/{user,account,transaction,category,budget,goal}.py`.
- Para birimi cent olarak saklama gerekçesi: `backend/app/models/transaction.py:23`.
- RLS bağlamı (`user_context_db()`): `docs/audit/improvement-sections/F-security.md` ve
  `docs/audit/diagrams/security-topology.md`.
- W3'te eklenen ek indeksler: `backend/migrations/versions/a1b2c3d4e5f6_audit_catchup_indexes.py`.
- BE-PERF-008 fonksiyonel indeks (`abs(amount_cents)`):
  `backend/migrations/versions/b2c3d4e5f6a7_functional_abs_amount_cents_index.py`.
