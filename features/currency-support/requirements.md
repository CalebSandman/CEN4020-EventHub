- **Currency Support-001** (ubiquitous): The {EventHub} shall allow users to select a supported currency before purchasing.  

- **Currency Support-002** (ubiquitous): The {EventHub} shall display ticket prices in the user's selected currency.  

- **Currency Support-003** (ubiquitous): The {EventHub} shall charge/calculate the purchase total using the selected currency.  

- **Currency Support-004** (ubiquitous): The {EventHub} shall use exchange rates stored in a config file that can be updated manually. 

- **Currency Support-005** (ubiquitous): The {EventHub} shall reject unsupported currencies.  

- **Currency Support-006** (ubiquitous): The {EventHub} shall not trust currency values supplied by the client without server-side validation.  

- **Currency Support-007** (ubiquitous): The system shall allow exchange rates to be updated either internally or by an external service. superseded by Currency Support-009

- **Currency Support-008** (ubiquitous): The {EventHub} shall use a single pricing component to calculate base prices, quantity-based totals, discount eligibility, and currency conversions.

- **Currency Support-009** (ubiquitous): The {EventHub} shall store exchange rates in a form that supports updates independently of software releases
    supercedes Currency Support-007

- **Currency Support-010** (ubiquitous): The {EventHub} shall account for the decimal precision of each supported currency when representing and calculating monetary values.