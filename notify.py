import datetime
import model
import utils

_status = {"prev_day": 0, "prev_hour": -1, "sent_morning_reminders": False, "hour_last_morning_reminder": -1, "hour_last_afternoon_reminder": -1, "hour_last_evening_reminder": -1}
BASE_URL = "http://zee.cortexlab.net"

def check_and_dispatch():
    global _status
    day = datetime.datetime.now().day
    hour = datetime.datetime.now().hour
    # Run this function at most once per hour
    if _status['prev_day'] == day and _status['prev_hour'] == hour:
        return
    if day != _status['prev_day']: # Reset everything
        _status = {"prev_day": day,
                   "prev_hour": hour,
                   "sent_morning_reminders": 0,
                   "hour_last_morning_reminder": -1,
                   "hour_last_afternoon_reminder": -1,
                   "hour_last_evening_reminder": -1}
    _status['prev_hour'] = hour
    carts = model.get_scheduled_carts(last_day=utils.today())
    # If it is after 6:00 AM and we have not yet sent out morning reminders
    if hour >= 6 and not _status["sent_morning_reminders"]:
        # Set the flag to true first.  That way, if there is an error sending
        # email to someone, it won't keep trying at every page request.
        _status["sent_morning_reminders"] = True 
        for c in carts.values():
            if c['person_id'] < 0:
                continue
            person = model.get_person_info(c['person_id'])
            msg = f"You are registered for {c['morning_afternoon_string']} rota today.  Don't forget!"
            utils.send_email(person['email'], "You are on rota today", msg)
    # After a given time of day, start sending out "did you forget to do the
    # rota" notifications to people every hour to make sure they don't forget.
    # That time of day is given by rota_times.
    rota_times = {1: 10, 2: 2, 3: 7}
    for morning_afternoon in [1, 2, 3]:
        if hour < rota_times[morning_afternoon]:
            continue
        cart = next((c for c in carts.values() if c['morning_afternoon'] == morning_afternoon), None)
        if cart is not None and not cart['completed'] and cart['person_id'] >= 0:
            person = model.get_person_info(cart['person_id'])
            utils.send_email(person['email'], "Don't forget to do the rota!", f"You are assigned to the {cart['morning_afternoon_string']} today, which has not been done yet.  If you are planning to do it soon, you can ignore this email.  If you have already done it, mark it as done on the 'Do rota' page.")
        
