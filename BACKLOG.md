Bugs and Features BACKLOG:

- [ ] Use the click popup modal event for the transactions table too - when clicking on the merchant.
- [ ] Add another chart that shows the integral of the first chart (ie. the balance)
- [ ] When filtering on account, and using the stacked checkbox, the categories are not the subset applicable to the account, but rather all of them.  This is incorrect.
- [ ] Single apostrophe (') in merchants table prevents the click for popup modal
- [ ] Default sort order for merchant should be Date descending

- [x] Include a column on the merchants view with most recently used date (for the merchant).  Also the number of times used.
- [x] Add a filter to the top of the transactions dashboard to select accounts.
- [x] The Total value shoudl move from the left of the graph to a better place.
- [ ] I would like to standardize the table control such that the mechanisms of a table are a general solution for all tables (eg. sorting by column toggles, filters by column, etc.). Currently some of these features are implemented for the transactions view while others are implemented for the merchants view.   I would like to consolidate these table mechanics features and then have all table views take advantage of the full set of table features.   The result should be a standardized feature rich table control that is used everywhere.