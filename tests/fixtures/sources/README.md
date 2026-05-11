# Source Fixtures

`springer-elements-robotics-ch12-image-processing.pdf` is the open-access
chapter "Image Processing" from *Elements of Robotics*:

- Authors: Mordechai Ben-Ari and Francesco Mondada
- DOI: https://doi.org/10.1007/978-3-319-62533-1_12
- Publisher page: https://link.springer.com/chapter/10.1007/978-3-319-62533-1_12

The fixture is intentionally checked in so advanced end-to-end tests can run
offline against a realistic academic PDF with prose, figures, formulas, and
tables.

Use this fixture for local smoke tests and deterministic visual QA examples:

- PDF ingestion and page-count/hash checks.
- Source page previews and zoom crops.
- Beamer rendering and Tectonic compilation tests.
- Deck preview and visual artifact metadata checks.

Before a public release, verify that the upstream open-access terms permit
redistribution of this checked-in PDF in the repository. If redistribution is not
acceptable, replace it with a smaller fixture whose license is explicit and keep
the same test coverage shape.
