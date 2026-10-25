# Assignment 4 submission status

## Design-change report: evidence available, report still required

Explain how Call 4 affected implementation and why, distinguishing existing Call 3 design from
new decisions. Evidence includes the modular application factory, centralized pricing and audit
services, isolated discount eligibility, money decision record, contributing rules, automated
checks and documented unanswered business questions. The root and application C4 models are
currently identical; do not claim diagram revisions that did not happen.

## AI process report: original history needed

The original implementer must supply actual prompts, generated outputs, review findings and
iterations. Do not invent this history. Explain initial completeness/correctness, how problems
were discovered, what prompts or manual changes corrected them, and the final test results.
The review found 200 existing tests passing but also uncovered Unicode CSRF and oversized-ID
crashes, unaudited anonymous attempts, absent CI and incorrect nested-repository hook paths.
The follow-up adds regression tests and repairs those issues. This is evidence about the
follow-up review, not proof of the original generation process or human review before merging.

## Remaining external decisions and verification

- Recover the previously settled ticket-hold, discount-scope, confirmation and purchase-limit
  answers from the customer emails. Current placeholders are not confirmed business rules.
- Confirm the discount percentage, session policy and audit retention.
- Obtain agreement to revise the screenshot-prevention requirement; no website can enforce it.
- Require the CI checks through repository branch protection and obtain another person's review.
- Verify event cards, checkout, currency selection and admin screens in desktop and mobile
  browsers, including keyboard access, touch, overflow and repeated submissions.
- Attach the two reports, application source and unit tests to the submission.
