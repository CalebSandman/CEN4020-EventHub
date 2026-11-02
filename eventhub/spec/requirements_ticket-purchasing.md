- **ticket-purchasing-001** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a ticket quantity. 

- **ticket-purchasing-002** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a supported currency. 

- **ticket-purchasing-003** (event-driven): When a user selects checkout, {EventHub} shall display the selected quantity, currency, event, and total cost. 

- **ticket-purchasing-004** (event-driven): When a purchase is completed, {EventHub} shall display a purchase confirmation. 

- **ticket-purchasing-005** (ubiquitous): The {EventHub} shall support purchasing tickets using a pretend/mock payment process.  

- **ticket-purchasing-006** (ubiquitous): The {EventHub} shall not integrate with an external payment provider.  

- **ticket-purchasing-007** (ubiquitous): The {EventHub} shall ensure that users cannot purchase more tickets than are available.  

- **ticket-purchasing-008** (unwanted): If tickets become unavailable before the purchase is completed, then {EventHub} shall display an error message for insufficient ticket availability.  

- **ticket-purchasing-009** (ubiquitous): The {EventHub} shall have a fixed ticket capacity for each event.  

- **ticket-purchasing-010** (event-driven): When a buyer attempts to purchase a ticket, the {EventHub} shall verify that the buyer is logged in, the requested ticket quantity is valid, the event exists and is not sold out, and the selected currency is supported before completing the purchase.

- **ticket-purchasing-011** (event-driven): When multiple buyers attempt to purchase tickets concurrently, the {EventHub} shall prevent the total number of tickets sold from exceeding the available inventory.

- **ticket-purchasing-012** (event-driven): When a buyer initiates a purchase, the {EventHub} shall process the purchase through identity verification, event validation, pricing, inventory management, and audit logging.

- **ticket-purchasing-013** (event-driven): When buyer initiates a purchase, the {EventHub} shall check ticket availability and decrements inventory as one operation.

- **ticket-purchasing-014** (event-driven): When a buyer abandons checkout, the {EventHub} shall handle the abandoned checkout without corrupting purchase data.