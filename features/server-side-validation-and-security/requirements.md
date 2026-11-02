- **server-side-validation-and-security-001** (ubiquitous): The {EventHub} shall validate ticket quantity inputs on the server.  

- **server-side-validation-and-security-002** (ubiquitous): The {EventHub} shall reject zero ticket quantities.  

- **server-side-validation-and-security-003** (ubiquitous): The {EventHub} shall reject negative ticket quantities.  

- **server-side-validation-and-security-004** (ubiquitous): The {EventHub} shall reject excessively large quantities.  

- **server-side-validation-and-security-005** (ubiquitous): The {EventHub} shall validate currency inputs against the supported currency list on the server.  

- **server-side-validation-and-security-006** (event-driven): When data enters through an external boundary, the {EventHub} shall validate the data before processing it, including form fields, ticket quantities, and currency codes. superseded by system-001

- **server-side-validation-and-security-007** (ubiquitous): The {EventHub} shall enforce role-based access control to prevent buyers from performing administrator-only actions.

- **server-side-validation-and-security-008** (event-driven): When a buyer attempts to access administrator functionality, the {EventHub} shall deny access.

- **server-side-validation-and-security-009** (event-driven): When an administrator accesses administrator functionality, the {EventHub} shall permit access only if the user is authorized for that functionality.

- **server-side-validation-and-security-010** (ubiquitous): The {EventHub} shall prevent buyer-facing functionality from invoking administrator-only functionality.