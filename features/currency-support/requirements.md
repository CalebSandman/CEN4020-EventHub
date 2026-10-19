- **currency-support-001** (ubiquitous): The {EventHub} shall allow users to select a supported currency before purchasing.  

- **currency-support-002** (ubiquitous): The {EventHub} shall display ticket prices in the user's selected currency.  

- **currency-support-003** (ubiquitous): The {EventHub} shall charge/calculate the purchase total using the selected currency.  

- **currency-support-004** (ubiquitous): The {EventHub} shall use exchange rates stored in a config file that can be updated manually. 

- **currency-support-005** (ubiquitous): The {EventHub} shall reject unsupported currencies.  

- **currency-support-006** (ubiquitous): The {EventHub} shall not trust currency values supplied by the client without server-side validation.  

- **currency-support-007** (ubiquitous): The {EventHub} shall allow exchange rates to be updated either internally or by an external service. superseded by currency-support-009

- **currency-support-008** (ubiquitous): The {EventHub} shall use a single pricing component to calculate base prices, quantity-based totals, discount eligibility, and currency conversions.

- **currency-support-009** (ubiquitous): The {EventHub} shall store exchange rates in a form that supports updates independently of software releases.
    supercedes currency-support-007

- **currency-support-010** (ubiquitous): The {EventHub} shall account for the decimal precision of each supported currency when representing and calculating monetary values.