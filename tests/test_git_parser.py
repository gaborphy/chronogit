from chronogit.git_parser import parse_repo

def test_parse():
    assert callable(parse_repo)
