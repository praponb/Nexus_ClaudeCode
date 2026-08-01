<!-- Example/test fixture only -- not real project requirements. -->

# Specification: Team Task Tracker

## Goal

A small team task tracker where users can create projects, add tasks to a
project, assign a status (todo/doing/done), and see a simple dashboard of
task counts per status.

## Functional requirements

- REQ-1: A user can create a project with a name and optional description.
- REQ-2: A user can add a task to a project with a title, description,
  status, and optional due date.
- REQ-3: A user can change a task's status.
- REQ-4: A user can view a dashboard showing task counts per status across
  all of their projects.
- REQ-5: A user can sign up and log in with an email and password.

## Non-functional requirements

- The API must respond to standard CRUD operations within 300ms under
  light load.
- All data must be scoped to the authenticated user (no cross-user access).
