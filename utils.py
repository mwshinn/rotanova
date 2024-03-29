from collections import Counter
import datetime
import email_secrets as secrets

from smtplib import SMTP
from email.mime.text import MIMEText

BASE_DATE_FORMAT = "%Y-%m-%d"
PRETTY_DATE_FORMAT = "%a %b %-d"

def compute_tab_changes(who_is_doing_rota, active_cages, morning_afternoon):
    # Deduct points proportional to how many total cages there were that day.
    count_person_cages_total = Counter([c['person_id'] for c in active_cages if not c['no_cost']])
    count_person_cages_thistime = Counter([c['person_id'] for c in active_cages if c['morning_afternoon'] == morning_afternoon and not c['no_cost']])
    total_cages = sum(count_person_cages_total.values())
    people_changes = { person : -count_person_cages_thistime[person]/total_cages for person in count_person_cages_total.keys()}
    # Give a point to the person who did rota
    if who_is_doing_rota >= 0:
        if who_is_doing_rota not in people_changes.keys():
            people_changes[who_is_doing_rota] = 0
        people_changes[who_is_doing_rota] += 1

    return people_changes

def today(offset=0):
    """Define this here so we can monkey patch it in the tests"""
    return datetime.date.today() + datetime.timedelta(offset)

def now():
    """Define this here so we can monkey patch it in the tests"""
    return datetime.datetime.now()

def format_date(date, pretty=False):
    fmt = BASE_DATE_FORMAT if not pretty else PRETTY_DATE_FORMAT
    return date.strftime(fmt)

def send_email(to, subject, body):
    print(f"Email to: {to}, Subject: {subject}\n\n{body}\n", flush=True)
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = f"\"Rota nova\" <{secrets.USERNAME}>"
    msg['To'] = to
    with SMTP(secrets.SERVER, secrets.PORT) as smtp_server:
        smtp_server.starttls()
        smtp_server.login(secrets.USERNAME, secrets.PASSWORD)
        smtp_server.sendmail(secrets.USERNAME, [to], msg.as_string())

def hash_carts(carts):
    """For detecting race conditions when editing the rota schedule"""
    return str(hash(str(carts)))
