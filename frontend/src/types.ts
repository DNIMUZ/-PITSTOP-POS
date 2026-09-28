export type Role = "admin" | "manager" | "cashier";

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface Category {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  barcode: string | null;
  category_id: number | null;
  category_name: string | null;
  unit_price: string;
  cost_price: string | null;
  image_url: string | null;
  description: string | null;
  is_active: boolean;
  stock_on_hand: number;
  reorder_level: number;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface TransactionItem {
  id: number;
  product_id: number;
  product_name: string;
  sku: string;
  unit_price: string;
  quantity: number;
  line_total: string;
}

export interface Payment {
  id: number;
  method: string;
  status: string;
  transaction_reference: string | null;
  amount: string;
}

export interface RefundItem {
  id: number;
  transaction_item_id: number;
  product_id: number;
  quantity: number;
  amount: string;
}

export interface Refund {
  id: number;
  refund_no: string;
  transaction_id: number;
  amount: string;
  reason: string | null;
  created_at: string;
  items: RefundItem[];
}

export interface TransactionListItem {
  id: number;
  transaction_no: string;
  cashier_id: number;
  cashier_name: string | null;
  items_count: number;
  subtotal: string;
  discount_rate: string;
  discount_amount: string;
  tax_rate: string;
  tax_amount: string;
  total: string;
  tendered_amount: string | null;
  change_amount: string | null;
  status: string;
  created_at: string;
}

export interface TransactionDetail {
  id: number;
  transaction_no: string;
  cashier_name: string | null;
  subtotal: string;
  discount_rate: string;
  discount_amount: string;
  tax_rate: string;
  tax_amount: string;
  total: string;
  tendered_amount: string | null;
  change_amount: string | null;
  status: string;
  created_at: string;
  items: TransactionItem[];
  payments: Payment[];
  refunds: Refund[];
}

export interface InventoryRow {
  product_id: number;
  sku: string;
  product_name: string;
  stock_on_hand: number;
  reorder_level: number;
}

export interface Movement {
  id: number;
  product_id: number;
  sku: string;
  product_name: string;
  quantity_change: number;
  reason: string;
  reference_type: string | null;
  note: string | null;
  created_at: string;
}

export interface DailyRevenue {
  day: string;
  revenue: string;
  orders: number;
}

export interface TopProduct {
  product_id: number;
  name: string;
  sku: string;
  quantity: number;
  revenue: string;
}

export interface LowStockItem {
  product_id: number;
  name: string;
  sku: string;
  stock_on_hand: number;
  reorder_level: number;
}

export interface Dashboard {
  revenue_today: string;
  orders_today: number;
  avg_order_value_today: string;
  items_sold_today: number;
  revenue_last_7_days: DailyRevenue[];
  top_products: TopProduct[];
  low_stock: LowStockItem[];
  generated_at: string;
}

export interface CartLine {
  product: Product;
  quantity: number;
}