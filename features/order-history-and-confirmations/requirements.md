- **order-history-and-confirmations-001** (ubiquitous): The {EventHub} shall maintain a history of a user's past orders.  

- **order-history-and-confirmations-002** (ubiquitous): The {EventHub} shall allow users to reopen a past order as a confirmation-style page.  

- **order-history-and-confirmations-003** (ubiquitous): The {EventHub} order confirmation page shall display event, quantity purchased, currency paid, exchange rate applied, and total paid. 

- **order-history-and-confirmations-004** (ubiquitous): The {EventHub} shall not allow the order confirmation page to be screenshotted 

- **order-history-and-confirmations-005** (event-driven): When a purchase is completed, the {EventHub} shall display the purchase confirmation on screen and shall not send a confirmation email.