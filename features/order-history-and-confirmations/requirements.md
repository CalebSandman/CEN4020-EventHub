- **Order History and Confirmations-001** (ubiquitous): The {EventHub} shall maintain a history of a user's past orders.  

- **Order History and Confirmations-002** (ubiquitous): The user shall be able to reopen a past order as a confirmation-style page.  

- **Order History and Confirmations-003** (ubiquitous): The order confirmation page shall display event, quantity purchased, currency paid, exchange rate applied, and total paid. 

- **Order History and Confirmations-004** (ubiquitous): The {EventHub} shall not allow the order confirmation page to be screenshotted 

- **Order History and Confirmations-004** (event-driven): When a purchase is completed, the system shall display the purchase confirmation on screen and shall not send a confirmation email.