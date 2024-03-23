Rota Nova
=========

Online system for managing the rota in cortexlab

Written by Max Shinn (m.shinn@ucl.ac.uk) - Dec 2023

Requirements
------------

Sqlalchemy and flask

How to use
----------

Each users has a "tab" of rota points.  Requesting a cage costs rota points, and
doing cart duties gains rota points.  The price per cage on a given day is [# of
your cages] / [total # of cages from everyone].  Bringing up the cart always
gains one rota point per day.  This system is not perfect, but it ensures that
the the net number of rota points per day is 0.  (There are two exceptions to
this: when more than one non-free-caage accounts do rota in a day, there will be
more than one rota points given out; and when cages get changed between morning
and afternoon rota, the sum may not equal zero because points are changed at the
moment the rota is finished.)  The cost is charged to your account at the time
the rota is performed.  If the cage is on the morning rota, you will be charged
in the morning, and if it is on afternoon rota, you will be charged in the
afternoon.

You may add cages to the rota using the "Cages" menu.  The "on behalf of" allows
you to add a cage for somebody else.  Both of these users will then have access
to the cage, but the "on behalf of" user is the one who will be "charged".  This
may be useful if you are an RA training animals for someone else.  You may also
leave notes about the cage which will be visible to the person performing the
rota.

When you perform the rota, log into your account and then click on "Do rota".
If you are scheduled for the rota, the list of cages you need to get will be
displayed.  Once you have collected all the cages in the BSU and are ready to go
back downstairs, click "Do Rota".  This will update all rota points and display
an indicator that the rota is done, preventing others for requesting cages for
this time/day.

To sign up for the rota, click on the "Schedule" link.  This will display a list
of who is performing the rota each day, and give you the option to sign up for
slots.  To sign up, click on the "Sign up" checkbox, and then press the "Save"
button at the bottom of the page.  You can sign up three weeks ahead of time.

There are currently no passwords on user accounts.  Rota nova is not written
with this type of security in mind.  Even if passwords were added to log in,
most operations do not check the current user to see if they have permissions to
perform it.  You could pretty easily inspect the POST requests and modify them
to do whatever you want.  (However, the server is safe: there should be no way
to read/write files on the remote server, execute server-side code, xss attacks,
etc.  Inputs are sanitised and IO is limited to the database.)

There are a few special types of accounts.  First, accounts can be listed as
"free cage" accounts.  These accounts do not participate in the rota points
system.  They may request as many cages as they want without being charged rota
points, and when they perform the rota, they do not gain rota points.

A second type of account is an "inactive" account.  These accounts may still log
in, but they are blocked from most activities, such as requesting cages and
performing the rota.

Last, there are admin accounts.  Admin accounts can do the following:

- Create new users, modify existing users, manually adjust their tab, and change
  normal users to the special user types listed above.
- Modify the rota schedule, assigning or changing anybody in any slot.
- Override the user who performed the rota on a specific day/time, proactively
  or retroactively.


Code organisation
-----------------

Code is organised, roughly, in a standard MVC architecture.  The file model.py
contains database access routines.  Currently sqlalchemy is used to access a
sqlite database, though this could easily be changed, because the rest of the
code depends only on the access functions 

Code is not at all optimised for database efficiency.  A single call that could
be done in one query with a join is done here using 10s or 100s of queries.  The
database is small (<500k) and this should not have more than 20 users making
requests a few times a day, so this isn't really a problem.  I don't notice a
delay.  I don't use the join features of the ORM because sqlalchemy really
doesn't like having multiple foreign keys from one table in another table.
E.g., here, cage owner and cage requester are both people.  It also doesn't like
when you need to use a non-key flag value.  E.g., here, "-2" means "no rota",
"-1" means "undefined", "-3" means user selectable, and 0-\infty means a user
id, i.e., a foreign key.  (Had I known this about sqlalchemy before starting, I
probably would have just used sqlite3 directly, but it really isn't worth it to
rewrite it now since, again, small database with few users making very few
requests.)  It should be easy to swap out the database engine if performance
ever becomes a problem.

The database has three tables:

- Cages: cages requested by users, NOT all cages that exist in the lab.  The
  owner is person_id (references the "People" table) and the person who
  requested the cage is "requested_by_id" (also from the "People" table).  The
  "start date" and "end date" is an inclusive range, so set them to the same day
  for a single-day request.  "morning_afternoon" can be either 1 (morning rota)
  or 2 (afternoon rota).  Rows can be safely deleted if their "end" date is in
  the past and when there are no more "Cart" rows with dates between the Cage
  "start" to "end" dates.
- People: list of rota users or people involved in the rota.  A "no_cost" user
  does not accumulate or spend rota points.  An active user can request cages
  and perform the rota.  The reason for including inactive users is to maintain
  rota points across long periods of absence and to avoid missing user
  references.  Only delete a row if you are sure the person is not referenced by
  any Cage or Cart rows.
- Carts: Not very well named, but an instance of performing the rota on a given
  date and time.  (It is short for "Cart duties".)  Usually this refers to
  signing up in the future, but can also refer to the past earlier in the same
  day (if the rota was performed) or any time in the past (if the rota was not
  performed).  Once it is performed, set the "complete" flag to true.  Any rows
  at least one day old whcih are completed can be deleted.  Uncompleted rotas
  mean that the points were not applied yet.  There are special user ids which
  are accepted here: -1 means none or invalid, -2 means no rota that day, and -3
  means users can sign up for these days.  (Fridays do not need to be set to -3
  as these allow signups by default.)  These userids are not valid elsewhere.

The template "base.html" is called by everything else.  It has blocks that can
be used to add content for everyone, for logged in users only, or for admins.

The logic for when and how to send notifications is hard-coded in notify.py.

