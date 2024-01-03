import sqlalchemy as sa
import sqlalchemy.orm as orm
import datetime
import utils

MORNING_AFTERNOON_STRING = {1: "morning", 2: "afternoon", 3: "evening"}

########## Database backend ##########

# These functions are used for the sqlalchemy ORM.  The rest of the code does
# not depend on these objects or on sqlalchemy in general, it depends only on
# the access functions below.  So you can swap this out for something different
# in the feature if your heart so desires.

class Base(orm.DeclarativeBase):
    def __repr__(self):
        kv = [f"{col.name}={getattr(self, col.name)}" for col in self.__table__.columns]
        return f"{self.__class__.__name__}({', '.join(kv)})"

class Cart(Base): # An instance of the rota being performed on a single day
    __tablename__ = "cart_instance"
    person_id = orm.mapped_column(sa.Integer) # -2 if no rota, -1 if undefined, or else foreign key from Person.id
    date = orm.mapped_column(sa.Date, primary_key=True)
    completed = orm.mapped_column(sa.Boolean)
    morning_afternoon = orm.mapped_column(sa.Integer, primary_key=True) # 1 = morning, 2 = afternoon, 3 = evening for now

class Person(Base):
    __tablename__ = "person"
    id = orm.mapped_column(sa.Integer, primary_key=True)
    name = orm.mapped_column(sa.String)
    email = orm.mapped_column(sa.String)
    no_cost = orm.mapped_column(sa.Boolean) # Whether this person collects rota points or gets free rota
    is_active = orm.mapped_column(sa.Boolean)
    is_admin = orm.mapped_column(sa.Boolean)
    tab = orm.mapped_column(sa.Float)

class Cage(Base):
    __tablename__ = "cage"
    id = orm.mapped_column(sa.Integer, primary_key=True)
    name = orm.mapped_column(sa.String)
    first_day = orm.mapped_column(sa.Date)
    last_day = orm.mapped_column(sa.Date)
    morning_afternoon = orm.mapped_column(sa.Integer) # 1 = morning, 2 = afternoon, 3 = evening for now
    person_id = orm.mapped_column(sa.Integer) # Should not be -2 or -1 (no rota or undefined)
    requested_by_id = orm.mapped_column(sa.Integer) # Should not be -2 or -1 (no rota or undefined)
    notes = orm.mapped_column(sa.String)
    request_datetime = orm.mapped_column(sa.DateTime)

engine = sa.create_engine("sqlite:///db.sqlite", echo=False)
Base.metadata.create_all(engine) # Only executes if a new database

########## Access functions ##########

# Interface between the ORM and the rest of the code.  If you swap out the
# RDBMS, please rewrite these but make sure they have the same output.


### People functions ###

def new_person(name, email, no_cost=False, tab=0, is_active=True, is_admin=False):
    with orm.Session(engine) as session:
        session.add_all([Person(name=name, email=email, no_cost=no_cost, is_active=is_active, tab=tab, is_admin=is_admin)])
        session.commit()

def edit_person(userid, name=None, email=None, no_cost=None, tab=None, is_active=None, is_admin=None, tab_change=None):
    with orm.Session(engine) as session:
        person_query = sa.select(Person).where(Person.id == userid)
        person = session.scalars(person_query).one()
        if name is not None:
            person.name = name
        if email is not None:
            person.email = email
        if no_cost is not None:
            person.no_cost = no_cost
        if tab is not None:
            person.tab = tab
        if tab_change is not None and not person.no_cost:
            person.tab += tab_change
        if is_admin is not None:
            person.is_admin = is_admin
        if is_active is not None:
            person.is_active = is_active
        session.commit()

def get_person_info(userid):
    q = sa.select(Person).where(Person.id == userid)
    with orm.Session(engine) as session:
        user = list(session.scalars(q))
    if len(user) == 1:
        return {col.name: getattr(user[0], col.name) for col in user[0].__table__.columns}
    elif len(user) == 0:
        return {"name": "N/A", "is_admin": False}
    else:
        raise ValueError("No such user")


def get_people(is_active=None, no_cost=None):
    q = sa.select(Person)
    if is_active is not None:
        q = q.where(Person.is_active == is_active)
    if no_cost is not None:
        q = q.where(Person.no_cost == no_cost)
    with orm.Session(engine) as session:
        ress = list(session.scalars(q))
        return [{col.name: getattr(res, col.name) for col in res.__table__.columns} for res in ress]

### Cage functions ###

def new_cage(name, first_day, last_day, morning_afternoon, person_id, requested_by_id=None, notes=""):
    if requested_by_id is None:
        requested_by_id = person_id
    with orm.Session(engine) as session:
        session.add(Cage(name=name, first_day=datetime.date(*map(int, first_day.split("-"))), last_day=datetime.date(*map(int, last_day.split("-"))), morning_afternoon=morning_afternoon, person_id=person_id, request_datetime=datetime.datetime.now(), notes=notes, requested_by_id=(requested_by_id if requested_by_id is not None else person_id)))
        session.commit()

def edit_cage(cage_id, name=None, first_day=None, last_day=None, morning_afternoon=None, person_id=None, requested_by_id=None, notes=None):
    with orm.Session(engine) as session:
        cage_query = sa.select(Cage).where(Cage.id == cage_id)
        cage = session.scalars(cage_query).one()
        if name is not None:
            cage.name = name
        if first_day is not None:
            if isinstance(first_day, str):
                first_day = datetime.date.fromisoformat(first_day)
            cage.first_day = first_day
        if last_day is not None:
            if isinstance(last_day, str):
                last_day = datetime.date.fromisoformat(last_day)
            cage.last_day = last_day
        if morning_afternoon is not None:
            cage.morning_afternoon = morning_afternoon
        if person_id is not None:
            cage.person_id = person_id
        if requested_by_id is not None:
            cage.requested_by_id = requested_by_id
        if notes is not None:
            cage.notes = notes
        session.commit()

def delete_cage(cage_id):
    with orm.Session(engine) as session:
        query = sa.select(Cage).where(Cage.id == cage_id)
        cage = session.scalars(query).one()
        session.delete(cage)
        session.commit()
        
        
def get_scheduled_cages(person_id=None, morning_afternoon=None, ignore_future=True):
    with orm.Session(engine) as session:
        q = session.query(Cage, Person).filter(Cage.person_id == Person.id).filter(Cage.last_day >= utils.today())
        if ignore_future:
            q = q.filter(Cage.first_day <= utils.today())
        if person_id is not None:
            q = q.filter(sa.or_(Cage.person_id == person_id, Cage.requested_by_id == person_id))
        if morning_afternoon is not None:
            q = q.filter(Cage.morning_afternoon == morning_afternoon)
        cage_person_pairs = q.all()
    res = []
    for cage,person in cage_person_pairs:
        res.append(dict(id=cage.id,
                        name=cage.name,
                        first_day=cage.first_day,
                        first_day_formatted=utils.format_date(cage.first_day),
                        last_day=cage.last_day,
                        last_day_formatted=utils.format_date(cage.last_day),
                        morning_afternoon=cage.morning_afternoon,
                        morning_afternoon_string=MORNING_AFTERNOON_STRING[cage.morning_afternoon],
                        person_id=cage.person_id,
                        notes=cage.notes,
                        request_datetime=cage.request_datetime,
                        person_name=person.name,
                        requested_by_id=cage.requested_by_id,
                        requested_by_name=get_person_info(cage.requested_by_id)['name'],
                        no_cost=person.no_cost))
    return res

### Cart functions ###

def schedule_cart(person_id, date, morning_afternoon, completed=False):
    with orm.Session(engine) as session:
        print("Scheduling", person_id, flush=True)
        session.add(Cart(person_id=person_id, date=datetime.date(*map(int, date.split("-"))), morning_afternoon=morning_afternoon, completed=completed))
        session.commit()

def reschedule_cart(date, morning_afternoon, person_id=None, completed=None, set_completed=None):
    """Return true if completion status changed from false to true.  Otherwise, return false."""
    print(date, morning_afternoon, person_id, completed, set_completed)
    with orm.Session(engine) as session:
        cart_query = sa.select(Cart).where(Cart.date == date).where(Cart.morning_afternoon == morning_afternoon)
        cart = session.scalars(cart_query).one()
        completion_status_begin = cart.completed
        if person_id == -1:
            print("Deleting", flush=True)
            session.delete(cart)
        else:
            if person_id is not None:
                cart.person_id = person_id
            if completed is not None:
                cart.completed = completed
            if set_completed is not None and not cart.completed:
                cart.completed = set_completed
        completion_status_end = cart.completed
        session.commit()
    return completion_status_end and not completion_status_begin

def get_scheduled_carts(first_day=None, last_day=None, person_id=None):
    with orm.Session(engine) as session:
        q = session.query(Cart, Person).filter(Cart.person_id.in_([Person.id, -1, -2]))
        if person_id is not None:
            q = q.filter(Cart.person_id == person_id)
        if first_day is not None:
            q = q.filter(Cart.date >= first_day)
        else:
            q = q.filter(Cart.date >= utils.today())
        if last_day is not None:
            q = q.filter(Cart.date <= last_day)
        cart_person_pairs = q.all()
    res = {}
    for cart,person in cart_person_pairs:
        date = utils.format_date(cart.date)
        res[(date, cart.morning_afternoon)] = dict(date=cart.date,
                                                   formatted_date=utils.format_date(cart.date),
                                                   morning_afternoon=cart.morning_afternoon,
                                                   morning_afternoon_string=MORNING_AFTERNOON_STRING[int(cart.morning_afternoon)],
                                                   person_id=int(cart.person_id),
                                                   person_name=person.name if int(cart.person_id)>=0 else "",
                                                   completed=cart.completed)
    return res

### Other ###

def cleanup():
    """Delete old entries in the database"""
    with orm.Session(engine) as session:
        cart_query = sa.select(Cart)
        carts = session.scalars(cart_query)
        for cart in carts:
            print(c)
            if cart.date < utils.today() and cart.complete:
                session.delete(cart)
        session.commit()
        cage_query = sa.select(Cage).where(Cage.first_day < utils.today()).where(Cage.last_day < utils.today())
        cages = session.scalars(cages_query)
        for cage in cages:
            to_delete = True
            for cart in carts:
                if cage.first_day <= cart.date and cart.date <= cage.last_day:
                    to_delete = False
                    break
            if to_delete:
                session.delete(cage)
        session.commit()

if len(get_people()) == 0:
    new_person("max", is_admin=True, email="max@maxshinnpotential.com")
    new_person("Charlie", email="charlie@gmail.com")
    new_cage("MS002", "2023-12-02", "2024-12-13", 1, 1)
    schedule_cart(1, "2024-1-02", 1, completed=True)
    schedule_cart(2, "2024-1-03", 3)
    schedule_cart(2, "2024-01-11", 1, completed=True)
