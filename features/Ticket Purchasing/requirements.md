- **Ticket Purchasing-001** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a ticket quantity. 

- **Ticket Purchasing-002** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a supported currency. 

- **Ticket Purchasing-003** (event-driven): When a user selects checkout, {EventHub} shall display the selected quantity, currency, event, and total cost. 

- **Ticket Purchasing-004** (event-driven): When a purchase is completed, {EventHub} shall display a purchase confirmation. 

- **Ticket Purchasing-005** (ubiquitous): The {EventHub} shall support purchasing tickets using a pretend/mock payment process.  

- **Ticket Purchasing-006** (ubiquitous): The {EventHub} shall not integrate with an external payment provider.  

- **Ticket Purchasing-007** (ubiquitous): The {EventHub} shall ensure that users cannot purchase more tickets than are available.  

- **Ticket Purchasing-008** (unwanted): If tickets become unavailable before the purchase is completed, then {EventHub} will display an error message for insufficient ticket availability.  

- **Ticket Purchasing-009** (ubiquitous): The {EventHub} shall have a fixed ticket capacity for each event.  