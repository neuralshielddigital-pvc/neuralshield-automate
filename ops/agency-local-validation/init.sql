-- Public synthetic credentials, usable only in this disposable offline fixture.
CREATE ROLE agency_test LOGIN PASSWORD 'synthetic-test-only'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
REVOKE ALL ON DATABASE nsd_agency_test_delivery FROM PUBLIC;
GRANT CONNECT, CREATE, TEMPORARY ON DATABASE nsd_agency_test_delivery TO agency_test;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
