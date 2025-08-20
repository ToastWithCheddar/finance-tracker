"""remove_audit_system

Revision ID: remove_audit_system
Revises: 9e561d011f4c
Create Date: 2025-08-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'remove_audit_system'
down_revision: Union[str, None] = '9e561d011f4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove audit triggers from all tables
    tables_to_audit = ['transactions', 'budgets', 'goals', 'categories', 'accounts']
    
    for table in tables_to_audit:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_audit_trigger ON {table};")
    
    # Drop the audit trigger function
    op.execute("DROP FUNCTION IF EXISTS log_changes();")
    
    # Drop audit log table and related objects
    op.drop_index(op.f('ix_audit_log_table_name'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_row_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_action'), table_name='audit_log')
    op.drop_table('audit_log')
    
    # Drop the audit action enum
    op.execute("DROP TYPE IF EXISTS auditaction;")


def downgrade() -> None:
    # Recreate the audit action enum
    op.execute("CREATE TYPE auditaction AS ENUM ('INSERT', 'UPDATE', 'DELETE');")
    
    # Recreate audit_log table
    op.create_table('audit_log',
    sa.Column('user_id', sa.Uuid(), nullable=True, comment='User who performed the action, null for system actions'),
    sa.Column('table_name', sa.String(length=100), nullable=False, comment='Name of the table that was modified'),
    sa.Column('row_id', sa.Uuid(), nullable=False, comment='Primary key of the affected record'),
    sa.Column('action', sa.Enum('INSERT', 'UPDATE', 'DELETE', name='auditaction'), nullable=False, comment='Type of action performed (INSERT, UPDATE, DELETE)'),
    sa.Column('old_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Complete record data before the change (null for INSERT)'),
    sa.Column('new_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Complete record data after the change (null for DELETE)'),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_row_id'), 'audit_log', ['row_id'], unique=False)
    op.create_index(op.f('ix_audit_log_table_name'), 'audit_log', ['table_name'], unique=False)

    # Recreate the generic audit trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION log_changes()
        RETURNS TRIGGER AS $$
        DECLARE
            v_old_data jsonb;
            v_new_data jsonb;
            v_user_id uuid;
        BEGIN
            -- Try to get the user_id from the current session configuration
            BEGIN
                v_user_id := current_setting('app.current_user_id')::uuid;
            EXCEPTION WHEN OTHERS THEN
                v_user_id := NULL;
            END;

            IF (TG_OP = 'UPDATE') THEN
                v_old_data := to_jsonb(OLD);
                v_new_data := to_jsonb(NEW);
                INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
                VALUES (v_user_id, TG_TABLE_NAME, OLD.id, 'UPDATE', v_old_data, v_new_data);
                RETURN NEW;
            ELSIF (TG_OP = 'DELETE') THEN
                v_old_data := to_jsonb(OLD);
                INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
                VALUES (v_user_id, TG_TABLE_NAME, OLD.id, 'DELETE', v_old_data, NULL);
                RETURN OLD;
            ELSIF (TG_OP = 'INSERT') THEN
                v_new_data := to_jsonb(NEW);
                INSERT INTO audit_log (user_id, table_name, row_id, action, old_data, new_data)
                VALUES (v_user_id, TG_TABLE_NAME, NEW.id, 'INSERT', NULL, v_new_data);
                RETURN NEW;
            END IF;
            RETURN NULL; -- result is ignored since this is an AFTER trigger
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Attach audit triggers to key tables
    tables_to_audit = ['transactions', 'budgets', 'goals', 'categories', 'accounts']
    
    for table in tables_to_audit:
        op.execute(f"""
            CREATE TRIGGER {table}_audit_trigger
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION log_changes();
        """)