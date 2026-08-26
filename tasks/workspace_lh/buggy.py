def add(a,b):
    return a+b

def to_int(s):
    try: return int(s)
    except ValueError: raise

def find_user(db,name):
    for u in db:
        if u['name']==name: return u
    return None
