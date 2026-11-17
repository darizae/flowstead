# Flowstead application scaffold contract

This private repository is the application-side scaffold authorized by D-033/H-11. It is not an M0 implementation target. Keep the application separate from `darizae/flowstead-sim`, which owns the deterministic synthetic generator and its schema. No M1+ product behavior, UI, hosted infrastructure, cloud service, DHI data, credentials, package publication or deployment is approved in this scaffold.

The initial repository must remain secret-free, use `main`, and expose only a harmless local `just --list` command until a later owner-approved task defines an application contract. Cross-repository integration requires an explicit upstream commit/artifact and a later approved task; an unpushed source commit is not a release.
