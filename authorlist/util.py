from datetime import datetime
import unidecode


def today():
    return datetime.utcnow().date().isoformat()

def validate_date(d):
    if not d:
        return None
    try:
        datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        return None
    return d

def validate_author(a):
    assert 'authname' in a
    assert 'collab' in a
    assert 'email' in a
    assert 'first' in a
    assert 'from' in a
    assert validate_date(a['from'])
    assert 'instnames' in a
    assert isinstance(a['instnames'], list)
    #assert 'keycloak_username' in a
    assert 'last' in a
    assert 'orcid' in a
    assert 'thanks' in a
    assert isinstance(a['thanks'], list)
    assert 'to' in a
    if a['to']:
        assert validate_date(a['to'])

def author_ordering(a):
    """
    The 'key' function in sorting authors.
    
    Sort authors using English unicode sorting rules.
    Secondary sorting by 'to', then 'collab', then 'from', then 'instnames'.
    """
    name = a['authname']
    parts = unidecode.unidecode(name).replace("'",'').split()
    ret = []
    for i,p in enumerate(reversed(parts)):
        if i == 0:
            ret.append(p)
        elif p[-1] == '.':
            ret += parts[:i+1]
            break
        else:
            ret[0] = p + ret[0]
    extras = [a['to'], a['collab'], a['from'], a['instnames']] if a['to'] else ['3000', a['collab'], a['from'], a['instnames']]
    return [x.lower() for x in ret]+extras
