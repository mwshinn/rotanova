import view
import flask
import sys
import model
import datetime
import utils
import log
import notify

app = flask.Flask(__name__, static_folder='res')

@app.before_request
def notifications():
    # Check if we need to send out nofifications, and 
    #try:
    notify.check_and_dispatch()
    #except Exception as e:
    #    log.log("Failed to send out email notifications", exception=str(e.exception), text=e.message)
        

@app.route("/login", methods=["POST"])
def set_user_cookie():
    userid = str(int(flask.request.form.get('user', -1)))
    redirect = flask.request.form.get('redirect', '')
    resp = flask.redirect("/"+redirect)
    resp.set_cookie('userid', userid)
    return resp

@app.route("/logout")
def logout():
    resp = flask.redirect("/")
    resp.set_cookie('userid', "-1")
    return resp

@app.route("/")
def home():
    return view.page_home()

@app.route("/admin")
def admin():
    return view.page_admin()

@app.route("/viewlog")
def viewlog():
    return view.page_viewlog()

@app.route("/users", methods=["GET", "POST"])
def users():
    userid = flask.request.form.get('person_id', None)
    if userid is not None:
        userid = int(userid)
        name = str(flask.request.form.get('person_name'))
        email = str(flask.request.form.get('person_email'))
        no_cost = flask.request.form['person_nocost'] == "yes"
        active = flask.request.form['person_active'] == "yes"
        is_admin = flask.request.form['person_admin'] == "yes"
        tab = float(flask.request.form['person_tab'])
        if userid >= 0:
            log.log("Modified user to be", modified_user_id=userid, name=name, email=email, no_cost=no_cost, is_active=active, is_admin=is_admin, tab=tab)
            model.edit_person(userid, name=name, email=email, no_cost=no_cost, is_active=active, is_admin=is_admin, tab=tab)
        elif userid == -1:
            log.log("New user", name=name, email=email, no_cost=no_cost, is_active=active, is_admin=is_admin, tab=tab)
            model.new_person(name=name, email=email, no_cost=no_cost, is_active=active, is_admin=is_admin, tab=tab)
    return view.page_users()

@app.route("/signup", methods=["GET", "POST"])
def signup():
    print("Signup started", flush=True)
    # Process all cart assignments
    carts = model.get_scheduled_carts()
    postvars = dict(flask.request.form)
    if len(postvars) > 0:
        userid = flask.request.cookies.get('userid', -1)
        for k,v in postvars.items():
            # Checkboxes for normal users
            if k.startswith("signup_"):
                _,morning_afternoon,date = k.split("_")
                log.log("New rota signup", signup_user=userid, date=date, morning_afternoon=int(morning_afternoon))
                model.schedule_cart(userid, date, int(morning_afternoon))
            # For admins scheduling people
            if k.startswith("person_"):
                _,morning_afternoon,date = k.split("_")
                person_id = int(v)
                if (date, int(morning_afternoon)) not in carts.keys():
                    if person_id != -1:
                        print("X", flush=True)
                        log.log("Cart scheduled", for_id=person_id, date=date, morning_afternoon=int(morning_afternoon))
                        model.schedule_cart(person_id, date, int(morning_afternoon))
                elif carts[(date, int(morning_afternoon))]['person_id'] != person_id:
                    print("Y", flush=True)
                    log.log("Cart rescheduled", for_id=person_id, date=date, morning_afternoon=int(morning_afternoon))
                    model.reschedule_cart(person_id=person_id, date=date, morning_afternoon=int(morning_afternoon))
    return view.page_signup()

@app.route("/dorota", methods=["GET", "POST"])
def dorota():
    is_rota_done = flask.request.form.get("rota_done", None)
    if is_rota_done is not None:
        print("ROta not done", flush=True)
        person_id = int(flask.request.form.get('person_id', -1))
        if person_id >= -2:
            print("User id good", flush=True)
            morning_afternoon = int(flask.request.form["morning_afternoon"])
            date = flask.request.form.get('date', -1)
            log.log("Rota completed", completed_by_id=person_id, date=date, morning_afternoon=morning_afternoon)
            completed_successful = model.reschedule_cart(date=date, morning_afternoon=morning_afternoon, person_id=person_id, set_completed=True)
            if completed_successful: # Apply rota points
                print("Applying rota points")
                active_cages = model.get_scheduled_cages()
                tab_changes = utils.compute_tab_changes(person_id, active_cages, morning_afternoon)
                log.log("Tabs updated", tab_deltas=",".join([f"{uid}:{nt}" for uid,nt in tab_changes.items()]))
                for person,change in tab_changes.items():
                    model.edit_person(person, tab_change=change)
    return view.page_dorota()

@app.route("/cages", methods=["GET", "POST"])
def cages():
    cageid = flask.request.form.get("cage_id", None)
    if "delete_cage" in flask.request.form.keys() and cageid is not None:
        log.log("Cage deleted", cage_id=cageid)
        model.delete_cage(cageid)
    elif cageid is not None:
        cageid = int(cageid)
        print(flask.request.form)
        name = flask.request.form["cage_name"]
        requester_id = flask.request.form["cage_requester"]
        first_day = flask.request.form.get('cage_start', None)
        last_day = flask.request.form.get('cage_end', None)
        morning_afternoon = flask.request.form['cage_morningafternoon']
        notes = flask.request.form['cage_notes']
        person_id = flask.request.form['cage_owner']
        if cageid == -1:
            log.log("New cage", name=name, first_day=first_day, last_day=last_day, morning_afternoon=morning_afternoon, scheduled_for=person_id, requester_id=requester_id)
            model.new_cage(name, first_day, last_day, morning_afternoon, person_id, requested_by_id=requester_id, notes=notes)
        else:
            log.log("Updated cage", name=name, first_day=first_day, last_day=last_day, morning_afternoon=morning_afternoon, scheduled_for=person_id, requester_id=requester_id)
            model.edit_cage(cageid, name, first_day, last_day, morning_afternoon, person_id, requested_by_id=requester_id, notes=notes)
    return view.page_cages()