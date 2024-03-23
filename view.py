import model
import flask
import utils
import log


def rota_today():
    # If it is a weekend, get the next weekday
    date = utils.today()
    date_offset = 0
    while date.weekday() >= 5:
        date_offset += 1
        date = utils.today(offset=date_offset) # Skip to next weekday
    datestr = utils.format_date(date)
    todays_rota = model.get_scheduled_carts(first_day=date, last_day=date)
    morning_rota =   todays_rota.get((datestr,1), {"person_id":-2})
    afternoon_rota = todays_rota.get((datestr,2), {"person_id":-2})
    evening_rota =   todays_rota.get((datestr,3), {"person_id":-2})
    rota_today = {1: morning_rota if morning_rota['person_id'] >= 0 else None, 
                  2: afternoon_rota if afternoon_rota['person_id'] >= 0 else None,
                  3: evening_rota if evening_rota['person_id'] >= 0 else None}
    return rota_today

def base_page_info():
    userid = flask.request.cookies.get('userid', -1)
    person = model.get_person_info(userid)
    people = model.get_people()
    date_today = utils.format_date(utils.today())
    return {
        "rota_today": rota_today(),
        "user_name": person['name'],
        "is_admin": person['is_admin'],
        "people": people,
        "userid": int(userid),
        "date_today": date_today,
        "weekday_today": utils.today().weekday()<5,
    }

def page_saved(msg, good=True):
    return flask.render_template("saved.html",
                                 msg=msg,
                                 pagetitle="Success" if good else "Failed",
                                 **base_page_info())

def page_home():
    cages_today_list = model.get_scheduled_cages()
    # Organise into a dict where the first index is person's id and the second
    # is morning_afternoon.  Use a special time of day of 0 which means all
    # cages.
    person_names = {}
    cages_today = {}
    for c in cages_today_list:
        if c['person_id'] not in cages_today.keys():
            cages_today[c['person_id']] = {0:[]}
            person_names[c['person_id']] = c['person_name']
        first_day = utils.format_date(c['first_day'], pretty=True)
        last_day = utils.format_date(c['last_day'], pretty=True)
        if c['morning_afternoon'] not in cages_today[c['person_id']]:
            cages_today[c['person_id']][c['morning_afternoon']] = []
        cageinfo = (c['name'], first_day, last_day, c['morning_afternoon'])
        cages_today[c['person_id']][c['morning_afternoon']].append(cageinfo)
        cages_today[c['person_id']][0].append(cageinfo)

    userid = flask.request.cookies.get('userid', -1)
    your_cages = [v for x in cages_today[userid].values() for v in x] if userid in cages_today.keys() else []
    return flask.render_template("home.html",
                                 pagetitle="Home",
                                 cages_today=cages_today,
                                 person_names=person_names,
                                 your_cages=your_cages,
                                 **base_page_info())

def page_users():
    return flask.render_template("users.html", pagetitle="Users", **base_page_info())

def page_signup(hasherror=False):
    _base_page_info = base_page_info()
    is_admin = _base_page_info['is_admin']
    _dates = [utils.today(offset=i) for i in range(0, 30 if is_admin else 22)]
    dates = [(utils.format_date(d, pretty=True), utils.format_date(d)) for d in _dates if d.weekday() < 5]
    carts = model.get_scheduled_carts()
    return flask.render_template("signup.html", pagetitle="Sign up", dates=dates, carts=carts, carts_hash=utils.hash_carts(carts), hasherror=hasherror, **_base_page_info)

def page_dorota():
    cages = {i : model.get_scheduled_cages(morning_afternoon=i) for i in [1, 2]}
    old_carts = model.get_scheduled_carts(first_day=utils.today(offset=-1000), last_day=utils.today(offset=-1))
    old_carts = {k : v for k,v in old_carts.items() if not v['completed']}
    return flask.render_template("dorota.html", pagetitle="Do rota", cages=cages, old_carts=old_carts, **base_page_info())
    
def page_cages():
    userid = flask.request.cookies.get('userid', -1)
    cages = model.get_scheduled_cages(person_id=userid, ignore_future=False)
    cages_everyone = model.get_scheduled_cages(ignore_future=False)
    return flask.render_template("cages.html", pagetitle="Cages", todayraw=utils.today(), cages=cages, cages_everyone=cages_everyone, **base_page_info())

def page_admin():
    return flask.render_template("admin.html", logtext=log.get_log(), **base_page_info())
