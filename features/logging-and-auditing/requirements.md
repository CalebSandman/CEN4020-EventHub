- **Logging and Auditing-001** (ubiquitous): The {EventHub} shall log every purchase attempt, regardless of whether it succeeds or fails.  

- **Logging and Auditing-002** (ubiquitous): The purchase attempt logs shall include timestamp, user, event, ticket quantity, currency, and purchase outcome (success/fail) 

- **Logging and Auditing-003** (ubiquitous): The {EventHub} shall provide distinct error messages for different failure conditions.  

- **Logging and Auditing-004** (ubiquitous): The {EventHub} shall distinguish between at least, sold-out tickets, invalid ticket quantities, and unsupported currencies. 

- **Logging and Auditing-005** (event-driven): When a complaint is investigated, the system shall allow the relevant audit log records to be reviewed manually.

- **Logging and Auditing-006** (event-driven): When a purchase attempt is processed, the system shall record the attempt through a centralized audit component.

- **Logging and Auditing-007** (ubiquitous): The system shall centralize audit logging in a dedicated component rather than relying on individual application routes to implement logging.

- **Logging and Auditing-008** (event-driven): When an administrator investigates a complaint, the system shall allow the administrator to review relevant audit records through the administrative interface.

- **Logging and Auditing-009** (ubiquitous): The system shall restrict access to audit records to authorized administrators.