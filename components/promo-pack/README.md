# Promo pack

One offer change in, one pack out. Every workflow the offer has to reach gets its own hand-off, and it starts.

1. Write the offer in the brand's offer bank: its lines word for word, and a row in the bank's promo calendar.
2. Plan the month with the marketing calendar. Its skill then starts the pack:

   ```
   python3 components/promo-pack/machine/pack.py tick --brand <brand> --month <YYYY-MM> --stock <runway.json>
   ```

3. Read `runs/promo-pack/<brand>/<moment>/PACK.md`: the words, the stock blockers, each hand-off and its state.

No approval step. Nothing it starts goes live, sends or spends money. Keys this tool needs: none.

Details: `CLAUDE.md`. The hand-offs: `definitions/handoffs.json`.
