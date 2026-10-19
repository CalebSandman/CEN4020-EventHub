- **user-accounts-and-authentication-001** (ubiquitous): The {EventHub} shall allow users from anywhere in the world to register for an account.  

- **user-accounts-and-authentication-002** (event-driven): When registering for an account, {EventHub} shall require a name, email, and password. 

- **user-accounts-and-authentication-003** (ubiquitous): The {EventHub} shall allow registered users to log in.  

- **user-accounts-and-authentication-004** (ubiquitous): The {EventHub} shall require users to be logged in to complete checkout.  

- **user-accounts-and-authentication-005** (ubiquitous): The {EventHub} shall require users to be logged in to view order history.  

- **user-accounts-and-authentication-006** (ubiquitous): The {EventHub} shall hash user passwords and shall not store them in plaintext. 

- **user-accounts-and-authentication-007** (ubiquitous): The {EventHub} shall support one user role. superseded by user-accounts-and-authentication-008

- **user-accounts-and-authentication-008** (ubiquitous): The {EventHub} shall support two user roles: buyer and administrator.
    supersedes: user-accounts-and-authentication-007

- **user-accounts-and-authentication-009** (event-driven): When an unauthenticated user attempts to access checkout or order history, the {EventHub} shall redirect the user to the login page.

- **user-accounts-and-authentication-010** (event-driven): When a user successfully logs in after requesting a protected page, the {EventHub} shall return the user to the originally requested page.

- **user-accounts-and-authentication-011** (state-driven): While a user is unauthenticated, the {EventHub} shall not display protected checkout or order history information.

- **user-accounts-and-authentication-012** (state-driven): While a user is unauthenticated, the {EventHub} shall not create a checkout or order record.

- **user-accounts-and-authentication-013** (event-driven): When an unauthenticated user navigates directly to a protected checkout or order history URL, the {EventHub} shall enforce the same authentication restrictions as normal navigation.