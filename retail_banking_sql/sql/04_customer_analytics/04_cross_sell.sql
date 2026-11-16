-- =====================================================================
-- CUSTOMERS 4 | CROSS-SELL: PRODUCT AFFINITY AND NEXT BEST PRODUCT
-- Business question: which products go together, and what should each
-- customer be offered next?
-- Techniques: self-join for market-basket pairs (support, confidence,
--             lift), anti-join with NOT EXISTS, ROW_NUMBER to keep the
--             best recommendation per customer.
-- =====================================================================

-- Products currently held by customers who are still with the bank.
CREATE VIEW analytics.current_holdings AS
SELECT DISTINCT h.customer_id, h.product_id
FROM marts.fact_product_holdings AS h
JOIN marts.dim_customer AS c USING (customer_id)
WHERE h.close_date IS NULL
  AND NOT c.is_closed;

-- support    = share of all customers holding both products
-- confidence = share of holders of A who also hold B
-- lift       = confidence / share of all customers holding B (>1 = affinity)
CREATE VIEW analytics.product_affinity AS
WITH total AS (
    SELECT COUNT(DISTINCT customer_id)::numeric AS customers FROM analytics.current_holdings
),
holders AS (
    SELECT product_id, COUNT(*)::numeric AS customers
    FROM analytics.current_holdings
    GROUP BY product_id
),
pairs AS (
    SELECT a.product_id AS product_a, b.product_id AS product_b, COUNT(*)::numeric AS customers
    FROM analytics.current_holdings AS a
    JOIN analytics.current_holdings AS b
      ON b.customer_id = a.customer_id AND b.product_id <> a.product_id
    GROUP BY a.product_id, b.product_id
)
SELECT p.product_a, pa.product_name AS if_customer_holds,
       p.product_b, pb.product_name AS then_also_holds,
       p.customers::integer                                   AS customers_with_both,
       ROUND(100 * p.customers / total.customers, 2)          AS support_pct,
       ROUND(100 * p.customers / ha.customers, 1)             AS confidence_pct,
       ROUND((p.customers / ha.customers) / (hb.customers / total.customers), 2) AS lift
FROM pairs AS p
CROSS JOIN total
JOIN holders AS ha ON ha.product_id = p.product_a
JOIN holders AS hb ON hb.product_id = p.product_b
JOIN marts.dim_product AS pa ON pa.product_id = p.product_a
JOIN marts.dim_product AS pb ON pb.product_id = p.product_b
WHERE p.product_a <> 1 AND p.product_b <> 1;      -- everyone holds a current account

-- One recommendation per customer: the product they do not hold with the
-- strongest affinity to something they already hold.
CREATE VIEW analytics.next_best_product AS
WITH candidates AS (
    SELECT h.customer_id,
           r.product_b                        AS product_id,
           r.then_also_holds                  AS recommended_product,
           r.if_customer_holds                AS because_customer_holds,
           r.confidence_pct, r.lift,
           ROW_NUMBER() OVER (PARTITION BY h.customer_id
                              ORDER BY r.lift DESC, r.confidence_pct DESC) AS rank_no
    FROM analytics.current_holdings AS h
    JOIN analytics.product_affinity AS r ON r.product_a = h.product_id
    JOIN marts.dim_customer AS c ON c.customer_id = h.customer_id
    WHERE r.lift >= 1.5
      AND r.customers_with_both >= 30
      -- eligibility: business loans for businesses, the rest for individuals
      AND ((c.customer_type = 'business' AND r.product_b NOT IN (4, 5, 8))
        OR (c.customer_type = 'personal' AND r.product_b <> 6))
      AND NOT EXISTS (SELECT 1 FROM analytics.current_holdings AS held
                      WHERE held.customer_id = h.customer_id
                        AND held.product_id = r.product_b)
)
SELECT customer_id, product_id, recommended_product, because_customer_holds,
       confidence_pct, lift
FROM candidates
WHERE rank_no = 1;

CREATE VIEW analytics.next_best_product_summary AS
SELECT recommended_product, because_customer_holds,
       COUNT(*)                     AS customers_to_contact,
       MAX(confidence_pct)          AS confidence_pct,
       MAX(lift)                    AS lift
FROM analytics.next_best_product
GROUP BY recommended_product, because_customer_holds
ORDER BY customers_to_contact DESC;
