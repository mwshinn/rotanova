import flask
import datetime
import re
import model

LOGFILE = "log.txt"

def _format_dict(**kwargs):
    args = []
    for k,v in kwargs.items():
        if v == "":
            v = '""'
        args.append(f"{k}={v}")
    return ", ".join(args)

def log(event_text, **kwargs):
    userid = int(flask.request.cookies.get('userid', -1))
    extra_info = {
        "ip_addr": flask.request.remote_addr,
        "ip_addr_noproxy": flask.request.environ.get("HTTP_X_FORWARDED_FOR", ""),
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "userid": userid,
        "username": model.get_person_info(userid)['name'] if userid >= 0 else ""
        }
    args = _format_dict(**kwargs, **extra_info)
    # Sanitize, just to be safe
    args = re.sub("[^A-Za-z0-9 _\\(\\)=\"\\.,:-]", "█", args)
    with open(LOGFILE, "a") as f:
        f.write(f"{event_text}: {args}\n")
    
def get_log():
    with open(LOGFILE, "r") as f:
        logtext = f.read()
    return logtext
