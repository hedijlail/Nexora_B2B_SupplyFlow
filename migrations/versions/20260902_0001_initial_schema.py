"""Initial B2B supplier platform schema."""
from alembic import op

revision = "20260902_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
    CREATE TYPE user_role AS ENUM ('owner','admin','sales','warehouse','accountant','viewer');
    CREATE TYPE order_status AS ENUM ('draft','confirmed','processing','fulfilled','cancelled');
    CREATE TYPE invoice_status AS ENUM ('draft','issued','partially_paid','paid','void');
    CREATE TYPE payment_status AS ENUM ('pending','completed','failed','refunded');
    CREATE TYPE stock_movement_type AS ENUM ('opening','receipt','sale','adjustment','transfer_in','transfer_out','return');

    CREATE TABLE companies (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name varchar(255) NOT NULL UNIQUE,
      slug varchar(100) NOT NULL UNIQUE, currency_code char(3) NOT NULL DEFAULT 'USD',
      is_active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE users (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id),
      email varchar(320) NOT NULL, password_hash varchar(255) NOT NULL, full_name varchar(255) NOT NULL,
      role user_role NOT NULL DEFAULT 'viewer', is_active boolean NOT NULL DEFAULT true, last_login_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(company_id, id), UNIQUE(company_id, email)
    );
    CREATE TABLE customers (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id),
      code varchar(80) NOT NULL, name varchar(255) NOT NULL, email varchar(320), phone varchar(50),
      tax_id varchar(100), address jsonb NOT NULL DEFAULT '{}'::jsonb, credit_limit numeric(14,2) NOT NULL DEFAULT 0,
      payment_terms_days integer NOT NULL DEFAULT 0, is_active boolean NOT NULL DEFAULT true, deleted_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(company_id,id), UNIQUE(company_id,code), CONSTRAINT customers_credit_limit_nonnegative CHECK (credit_limit >= 0),
      CONSTRAINT customers_payment_terms_nonnegative CHECK (payment_terms_days >= 0)
    );
    CREATE TABLE categories (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id),
      parent_id uuid, name varchar(255) NOT NULL, description text, is_active boolean NOT NULL DEFAULT true, deleted_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,name),
      FOREIGN KEY (company_id,parent_id) REFERENCES categories(company_id,id)
    );
    CREATE TABLE products (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), category_id uuid,
      sku varchar(100) NOT NULL, barcode varchar(100), name varchar(255) NOT NULL, description text,
      unit varchar(30) NOT NULL DEFAULT 'unit', cost_price numeric(14,2) NOT NULL DEFAULT 0, sale_price numeric(14,2) NOT NULL DEFAULT 0,
      is_active boolean NOT NULL DEFAULT true, deleted_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(company_id,id), UNIQUE(company_id,sku), UNIQUE(company_id,barcode),
      FOREIGN KEY(company_id,category_id) REFERENCES categories(company_id,id),
      CONSTRAINT products_cost_nonnegative CHECK(cost_price >= 0), CONSTRAINT products_sale_nonnegative CHECK(sale_price >= 0)
    );
    CREATE TABLE warehouses (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), code varchar(80) NOT NULL,
      name varchar(255) NOT NULL, address jsonb NOT NULL DEFAULT '{}'::jsonb, is_active boolean NOT NULL DEFAULT true, deleted_at timestamptz,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,code)
    );
    CREATE TABLE stocks (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), warehouse_id uuid NOT NULL, product_id uuid NOT NULL,
      quantity numeric(16,3) NOT NULL DEFAULT 0, reserved_quantity numeric(16,3) NOT NULL DEFAULT 0,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,warehouse_id,product_id),
      FOREIGN KEY(company_id,warehouse_id) REFERENCES warehouses(company_id,id), FOREIGN KEY(company_id,product_id) REFERENCES products(company_id,id),
      CONSTRAINT stocks_quantity_nonnegative CHECK(quantity >= 0), CONSTRAINT stocks_reserved_nonnegative CHECK(reserved_quantity >= 0),
      CONSTRAINT stocks_reserved_available CHECK(reserved_quantity <= quantity)
    );
    CREATE TABLE orders (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), customer_id uuid NOT NULL,
      order_number varchar(80) NOT NULL, status order_status NOT NULL DEFAULT 'draft', order_date timestamptz NOT NULL DEFAULT now(),
      notes text, subtotal numeric(14,2) NOT NULL DEFAULT 0, discount_total numeric(14,2) NOT NULL DEFAULT 0, tax_total numeric(14,2) NOT NULL DEFAULT 0, grand_total numeric(14,2) NOT NULL DEFAULT 0,
      created_by uuid, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,order_number),
      FOREIGN KEY(company_id,customer_id) REFERENCES customers(company_id,id), FOREIGN KEY(company_id,created_by) REFERENCES users(company_id,id),
      CONSTRAINT orders_totals_nonnegative CHECK(subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND grand_total >= 0)
    );
    CREATE TABLE order_items (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), order_id uuid NOT NULL, product_id uuid NOT NULL,
      quantity numeric(16,3) NOT NULL, unit_price numeric(14,2) NOT NULL, discount_amount numeric(14,2) NOT NULL DEFAULT 0, tax_amount numeric(14,2) NOT NULL DEFAULT 0, line_total numeric(14,2) NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id),
      FOREIGN KEY(company_id,order_id) REFERENCES orders(company_id,id) ON DELETE CASCADE, FOREIGN KEY(company_id,product_id) REFERENCES products(company_id,id),
      CONSTRAINT order_items_values_valid CHECK(quantity > 0 AND unit_price >= 0 AND discount_amount >= 0 AND tax_amount >= 0 AND line_total >= 0)
    );
    CREATE TABLE customer_pricing (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), customer_id uuid NOT NULL, product_id uuid NOT NULL,
      unit_price numeric(14,2) NOT NULL, min_quantity numeric(16,3) NOT NULL DEFAULT 1, valid_from date, valid_to date, is_active boolean NOT NULL DEFAULT true,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id),
      FOREIGN KEY(company_id,customer_id) REFERENCES customers(company_id,id), FOREIGN KEY(company_id,product_id) REFERENCES products(company_id,id),
      CONSTRAINT customer_pricing_values_valid CHECK(unit_price >= 0 AND min_quantity > 0),
      CONSTRAINT customer_pricing_date_range CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
    );
    CREATE TABLE invoices (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), customer_id uuid NOT NULL, order_id uuid,
      invoice_number varchar(80) NOT NULL, status invoice_status NOT NULL DEFAULT 'draft', issue_date date NOT NULL DEFAULT current_date, due_date date,
      subtotal numeric(14,2) NOT NULL DEFAULT 0, tax_total numeric(14,2) NOT NULL DEFAULT 0, grand_total numeric(14,2) NOT NULL DEFAULT 0, notes text,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,invoice_number),
      FOREIGN KEY(company_id,customer_id) REFERENCES customers(company_id,id), FOREIGN KEY(company_id,order_id) REFERENCES orders(company_id,id),
      CONSTRAINT invoices_totals_nonnegative CHECK(subtotal >= 0 AND tax_total >= 0 AND grand_total >= 0),
      CONSTRAINT invoices_due_date_valid CHECK(due_date IS NULL OR due_date >= issue_date)
    );
    CREATE TABLE payments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), invoice_id uuid NOT NULL,
      payment_number varchar(80) NOT NULL, status payment_status NOT NULL DEFAULT 'pending', amount numeric(14,2) NOT NULL,
      payment_date timestamptz, method varchar(50), reference varchar(120), notes text,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), UNIQUE(company_id,payment_number),
      FOREIGN KEY(company_id,invoice_id) REFERENCES invoices(company_id,id), CONSTRAINT payments_amount_positive CHECK(amount > 0)
    );
    CREATE TABLE stock_movements (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), warehouse_id uuid NOT NULL, product_id uuid NOT NULL,
      movement_type stock_movement_type NOT NULL, quantity_delta numeric(16,3) NOT NULL, reference_type varchar(50), reference_id uuid, notes text,
      performed_by uuid, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id),
      FOREIGN KEY(company_id,warehouse_id) REFERENCES warehouses(company_id,id), FOREIGN KEY(company_id,product_id) REFERENCES products(company_id,id), FOREIGN KEY(company_id,performed_by) REFERENCES users(company_id,id),
      CONSTRAINT stock_movements_delta_not_zero CHECK(quantity_delta <> 0)
    );
    CREATE TABLE audit_logs (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), actor_user_id uuid,
      action varchar(100) NOT NULL, entity_type varchar(100) NOT NULL, entity_id uuid, old_values jsonb, new_values jsonb, ip_address inet,
      created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,id), FOREIGN KEY(company_id,actor_user_id) REFERENCES users(company_id,id)
    );
    CREATE TABLE settings (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), company_id uuid NOT NULL REFERENCES companies(id), key varchar(120) NOT NULL, value jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(company_id,key)
    );

    CREATE INDEX ix_users_company_active ON users(company_id,is_active);
    CREATE INDEX ix_customers_company_active ON customers(company_id,is_active) WHERE deleted_at IS NULL;
    CREATE INDEX ix_products_company_active ON products(company_id,is_active) WHERE deleted_at IS NULL;
    CREATE INDEX ix_products_company_category ON products(company_id,category_id);
    CREATE INDEX ix_stocks_company_product ON stocks(company_id,product_id);
    CREATE INDEX ix_stock_movements_lookup ON stock_movements(company_id,warehouse_id,product_id,created_at DESC);
    CREATE INDEX ix_orders_customer_status ON orders(company_id,customer_id,status,order_date DESC);
    CREATE INDEX ix_order_items_order ON order_items(company_id,order_id);
    CREATE INDEX ix_invoices_customer_status ON invoices(company_id,customer_id,status,due_date);
    CREATE INDEX ix_payments_invoice ON payments(company_id,invoice_id);
    CREATE INDEX ix_audit_logs_entity ON audit_logs(company_id,entity_type,entity_id,created_at DESC);

    CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER companies_set_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER customers_set_updated_at BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER categories_set_updated_at BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER products_set_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER warehouses_set_updated_at BEFORE UPDATE ON warehouses FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER stocks_set_updated_at BEFORE UPDATE ON stocks FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER orders_set_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER order_items_set_updated_at BEFORE UPDATE ON order_items FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER customer_pricing_set_updated_at BEFORE UPDATE ON customer_pricing FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER invoices_set_updated_at BEFORE UPDATE ON invoices FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER payments_set_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    CREATE TRIGGER settings_set_updated_at BEFORE UPDATE ON settings FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS settings, audit_logs, stock_movements, payments, invoices, customer_pricing, order_items, orders, stocks, warehouses, products, categories, customers, users, companies CASCADE;
    DROP FUNCTION IF EXISTS set_updated_at();
    DROP TYPE IF EXISTS stock_movement_type, payment_status, invoice_status, order_status, user_role;
    """)
