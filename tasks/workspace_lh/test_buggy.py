from buggy import add, to_int, find_user
def test_add():
    assert add(2,3) == 5
def test_to_int_ok():
    assert to_int("42") == 42
def test_to_int_fail():
    try:
        to_int("abc"); assert False
    except ValueError:
        pass
def test_find():
    db=[{'name':'a'}]
    assert find_user(db,'a') == {'name':'a'}
    assert find_user(db,'x') is None
