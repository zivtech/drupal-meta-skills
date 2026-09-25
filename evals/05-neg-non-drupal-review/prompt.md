---
max_turns: 6
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---
Quick code review on this Express handler please — it's a plain Node service, nothing to do with our CMS.

`routes/orders.js`
```js
const express = require('express');
const router = express.Router();
const pool = require('../db');

router.get('/orders', (req, res) => {
  const customerId = req.query.customerId;
  const sql = "SELECT id, total, status FROM orders WHERE customer_id = '" + customerId + "'";

  pool.query(sql, (err, result) => {
    if (err) {
      console.log(err);
    }
    res.json(result.rows);
  });
});

module.exports = router;
```
