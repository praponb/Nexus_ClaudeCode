<!-- Example/test fixture only -- not a real project layout. -->

# Layout: Team Task Tracker

## Pages

- `/login` -- email/password sign in and sign up.
- `/dashboard` -- task counts per status, list of projects.
- `/projects/:id` -- task list for one project, grouped by status
  (todo/doing/done columns).

## Responsive behavior

- Desktop: three-column board layout for the project view.
- Mobile: single-column, status selectable via a tab strip.

## Accessibility

- All interactive controls reachable by keyboard.
- Status changes announced via an ARIA live region.
