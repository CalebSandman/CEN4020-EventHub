- **Server-Side Validation and Security-001** (ubiquitous): The ticket quantity inputs shall be validated on the server.  

- **Server-Side Validation and Security-002** (ubiquitous): The {EventHub} shall reject zero ticket quantities.  

- **Server-Side Validation and Security-003** (ubiquitous): The {EventHub} shall reject negative ticket quantities.  

- **Server-Side Validation and Security-004** (ubiquitous): The {EventHub} shall reject excessively large quantities.  

- **Server-Side Validation and Security-005** (ubiquitous): The {EventHub} shall validate currency inputs against {EventHub}'s supported currency list on the server.  

- **Server-Side Validation and Security-006** (event-driven): When data enters the system through an external boundary, the system shall validate the data before processing it, including form fields, ticket quantities, and currency codes.

- **Server-Side Validation and Security-007** (ubiquitous): The system shall enforce role-based access control to prevent buyers from performing administrator-only actions.

- **Server-Side Validation and Security-008** (event-driven): When a buyer attempts to access administrator functionality, the system shall deny access.

- **Server-Side Validation and Security-009** (event-driven): When an administrator accesses administrator functionality, the system shall permit access only if the user is authorized for that functionality.

- **Server-Side Validation and Security-010** (ubiquitous): The system shall prevent buyer-facing functionality from invoking administrator-only functionality.