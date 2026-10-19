- **User Accounts and Authentication-001** (ubiquitous): The {EventHub} shall allow users from anywhere in the world to register for an account.  

- **User Accounts and Authentication-002** (event-driven): When registering for an account, {EventHub} shall require a name, email, and password. 

- **User Accounts and Authentication-003** (ubiquitous): The {EventHub} shall allow registered users to log in.  

- **User Accounts and Authentication-004** (ubiquitous): The {EventHub} shall require users to be logged in to complete checkout.  

- **User Accounts and Authentication-005** (ubiquitous): The {EventHub} shall require users to be logged in to view order history.  

- **User Accounts and Authentication-006** (ubiquitous): The {EventHub} shall hash user passwords and shall not store them in plaintext. 

- **User Accounts and Authentication-007** (ubiquitous): The system shall support one user role. superseded by ___

- **User Accounts and Authentication-008** (ubiquitous): The {EventHub} shall support two user roles: buyer and administrator.
    supersedes: User Accounts and Authentication-007

- **User Accounts and Authentication-009** (event-driven): When an unauthenticated user attempts to access checkout or order history, the system shall redirect the user to the login page.

- **User Accounts and Authentication-010** (event-driven): When a user successfully logs in after requesting a protected page, the system shall return the user to the originally requested page.

- **User Accounts and Authentication-011** (state-driven): While a user is unauthenticated, the system shall not display protected checkout or order history information.

- **User Accounts and Authentication-012** (state-driven): While a user is unauthenticated, the system shall not create a checkout or order record.

- **User Accounts and Authentication-013** (event-driven): When an unauthenticated user navigates directly to a protected checkout or order history URL, the system shall enforce the same authentication restrictions as normal navigation.