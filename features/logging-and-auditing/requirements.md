- **logging-and-auditing-001** (ubiquitous): The {EventHub} shall log every purchase attempt, regardless of whether it succeeds or fails.  

- **logging-and-auditing-002** (ubiquitous): The {EventHub} purchase attempt logs shall include timestamp, user, event, ticket quantity, currency, and purchase outcome (success/fail) 

- **logging-and-auditing-003** (ubiquitous): The {EventHub} shall provide distinct error messages for different failure conditions.  

- **logging-and-auditing-004** (ubiquitous): The {EventHub} shall distinguish between at least, sold-out tickets, invalid ticket quantities, and unsupported currencies. 

- **logging-and-auditing-005** (event-driven): When a complaint is investigated, the {EventHub} shall allow the relevant audit log records to be reviewed manually.

- **logging-and-auditing-006** (event-driven): When a purchase attempt is processed, the {EventHub} shall record the attempt through a centralized audit component.

- **logging-and-auditing-007** (ubiquitous): The {EventHub} shall centralize audit logging in a dedicated component rather than relying on individual application routes to implement logging.

- **logging-and-auditing-008** (event-driven): When an administrator investigates a complaint, the {EventHub} shall allow the administrator to review relevant audit records through the administrative interface.

- **logging-and-auditing-009** (ubiquitous): The {EventHub} shall restrict access to audit records to authorized administrators.