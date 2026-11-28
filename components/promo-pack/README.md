# Promo pack

One offer change in, one pack out. Every workflow the offer has to reach gets its own hand-off.

1. Write the offer in the brand's offer bank: its lines word for word, and a row in the bank's promo calendar.
2. Plan the month with the marketing calendar.
3. Build the pack:

   ```
   python3 components/promo-pack/machine/pack.py build --brand <brand> --month <YYYY-MM> --stock <runway.json>
   ```

4. The owner reads `runs/promo-pack/<brand>/<moment>/PACK.md` and approves the offer words.
5. Hand it off: `pack.py hand --brand <brand> --moment <moment>`.

Nothing goes live, sends or spends from here. Keys this tool needs: none.

Details: `CLAUDE.md`. The hand-offs: `definitions/handoffs.json`.
