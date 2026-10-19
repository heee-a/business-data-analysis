# 数据仓库 schema 说明

- 模型：**星型模型（Star Schema）**
- 事实表：`fact_order_items`，粒度：一行 = 一张发票中的一个商品明细项
- 维度表：`dim_orders`、`dim_customers`、`dim_products`、`dim_date`

## 主外键关系

1. `fact_order_items.Invoice  → dim_orders.Invoice`
2. `fact_order_items.StockCode → dim_products.StockCode`
3. `fact_order_items.OrderDate → dim_date.Date`
4. `dim_orders.CustomerID → dim_customers.CustomerID`

## 表行数
| 表名 | 行数 |
|---|---|
| fact_order_items | 302,786 |
| dim_orders | 11,875 |
| dim_customers | 3,763 |
| dim_products | 4,507 |
| dim_date | 739 |