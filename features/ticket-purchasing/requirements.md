- **Ticket Purchasing-001** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a ticket quantity. 

- **Ticket Purchasing-002** (event-driven): When a user is purchasing tickets, {EventHub} shall allow the user to select a supported currency. 

- **Ticket Purchasing-003** (event-driven): When a user selects checkout, {EventHub} shall display the selected quantity, currency, event, and total cost. 

- **Ticket Purchasing-004** (event-driven): When a purchase is completed, {EventHub} shall display a purchase confirmation. 

- **Ticket Purchasing-005** (ubiquitous): The {EventHub} shall support purchasing tickets using a pretend/mock payment process.  

- **Ticket Purchasing-006** (ubiquitous): The {EventHub} shall not integrate with an external payment provider.  

- **Ticket Purchasing-007** (ubiquitous): The {EventHub} shall ensure that users cannot purchase more tickets than are available.  

- **Ticket Purchasing-008** (unwanted): If tickets become unavailable before the purchase is completed, then {EventHub} will display an error message for insufficient ticket availability.  

- **Ticket Purchasing-009** (ubiquitous): The {EventHub} shall have a fixed ticket capacity for each event.  

- **Ticket Purchasing-010** (event-driven): When a buyer attempts to purchase a ticket, the system shall verify that the buyer is logged in, the requested ticket quantity is valid, the event exists and is not sold out, and the selected currency is supported before completing the purchase.

- **Ticket Purchasing-011** (event-driven): When multiple buyers attempt to purchase tickets concurrently, the system shall prevent the total number of tickets sold from exceeding the available inventory.

- **Ticket Purchasing-012** (event-driven): When a buyer initiates a purchase, the system shall process the purchase through identity verification, event validation, pricing, inventory management, and audit logging.

- **Ticket Purchasing-013** (event-driven): When the system checks ticket availability and decrements inventory, it shall perform both operations as one atomic operation.

- **Ticket Purchasing-014** (event-driven): When a buyer abandons checkout, the system shall handle the abandoned checkout without corrupting purchase data.