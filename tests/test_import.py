from copy import deepcopy
from datetime import datetime
import logging
import pytest
from unittest.mock import AsyncMock

from authorlist.state import State
import import_from_keycloak


@pytest.fixture
def keycloak_fake(monkeypatch):
    # make sure the cache is always clear
    monkeypatch.setattr(import_from_keycloak, 'user_cache', {})

    # mock keycloak functions
    user_info = AsyncMock()
    monkeypatch.setattr(import_from_keycloak, 'user_info', user_info)

    get_group_membership = AsyncMock()
    monkeypatch.setattr(import_from_keycloak, 'get_group_membership', get_group_membership)

    list_insts = AsyncMock()
    monkeypatch.setattr(import_from_keycloak, 'list_insts_cached', list_insts)

    yield user_info, get_group_membership, list_insts


@pytest.mark.asyncio
async def test_get_keycloak_users(keycloak_fake):
    user_info, get_group_membership, list_insts = keycloak_fake

    user_data = {
        'user1': {
            'username': 'user1',
            'firstName': 'First',
            'lastName': 'Last',
            'email': 'user1@icecube.wisc.edu',
            'attributes': {},
        },
        'user2': {
            'username': 'user2',
            'firstName': 'First2',
            'lastName': 'Last2',
            'email': 'user2@icecube.wisc.edu',
            'attributes': {
                'author_firstName': 'NewFirst',
                'author_lastName': 'NewLast',
                'author_email': 'first2.last2@icecube.wisc.edu',
            },
        },
    }
    get_group_membership.return_value = ['user1', 'user2']
    def get_user(username, **kwargs):
        if username in user_data:
            return user_data[username]
        else:
            raise Exception('bad username')
    user_info.side_effect = get_user

    ret = await import_from_keycloak.get_keycloak_users('/foo/bar')

    get_group_membership.assert_called_once()
    user_info.assert_called()
    user2 = user_data['user2'].copy()
    user2['firstName'] = user2['attributes']['author_firstName']
    user2['lastName'] = user2['attributes']['author_lastName']
    user2['email'] = user2['attributes']['author_email']
    assert ret == [user_data['user1'], user2]

@pytest.mark.parametrize("test_input,expected", [
    ({'first': 'Test', 'last': 'Foo'}, 'tfoo'),
    ({'first': 'Test', 'last': 'Abcdef Ghijklmnop'}, 'tabcdefghijklmn'),
    ({'first': 'Carlos', 'last': 'Argüelles'}, 'carguelles'),
])
def test_make_username(test_input, expected):
    ret = import_from_keycloak.make_username(test_input)
    assert ret == expected


@pytest.mark.parametrize("author,user,expected", [
    ({'first': 'John', 'last': 'Doe', 'email': 'jdoe@icecube.wisc.edu', 'keycloak_username': 'jdoe'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     True),
    ({'first': 'John', 'last': 'Doe', 'email': 'jdoe@icecube.wisc.edu', 'keycloak_username': 'foo'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     False),
    ({'first': 'John', 'last': 'Doe', 'email': 'j.doe@icecube.wisc.edu'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     True),
    ({'first': 'J.', 'last': 'Doe', 'email': 'j.doe@icecube.wisc.edu'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     True),
    ({'first': 'Foo', 'last': 'Doe', 'email': 'foo@gmail.com'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe', 'email': 'foo@gmail.com'},
     True),
    ({'first': 'Foo', 'last': 'Doe', 'email': 'jdoe@icecube.wisc.edu'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     True),
    ({'first': 'Foo', 'last': 'Doe', 'email': 'foo@gmail.com'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe'},
     False),
    ({'first': 'John2', 'last': 'Doe', 'email': 'jdoe2@icecube.wisc.edu'},
     {'firstName': 'John', 'lastName': 'Doe', 'username': 'jdoe', 'email': 'jdoe@icecube.wisc.edu'},
     False),
])
def test_match_one(author, user, expected):
    ret = import_from_keycloak.match_one(author, user)
    assert ret == expected


AUTHOR_DATA = {
    'authors': [
        {
          "authname": "J. Doe",
          "collab": "icecube",
          "email": "j.doe@icecube.wisc.edu",
          "first": "John",
          "from": "2020-01-01",
          "instnames": [
            "inst1"
          ],
          "keycloak_username": "jdoe",
          "last": "Doe",
          "orcid": "0000-0001-0002-0003",
          "thanks": ['thanks1'],
          "to": ""
        },
        {
          "authname": "J. Doe",
          "collab": "icecube",
          "email": "jdoe2@icecube.wisc.edu",
          "first": "John2",
          "from": "2021-01-01",
          "instnames": [
            "inst2-astro"
          ],
          "last": "Doe",
          "keycloak_username": "jdoe2",
          "orcid": "0000-0001-0002-0003",
          "thanks": ['thanks2'],
          "to": ""
        },
    ],
    'institutions': {
        "inst1": {
          "cite": "Inst1, Some Place, City, Country",
          "city": "City",
          "collabs": [
            "icecube",
          ],
          "name": "Inst1",
          "keycloak_groups": ['/experiments/IceCube/inst1/authorlist'],
        },
        "inst2-astro": {
          "cite": "Inst2, Some Place, City, Country",
          "city": "City",
          "collabs": [
            "icecube",
          ],
          "name": "Inst2 Astro",
          "keycloak_groups": ['/experiments/IceCube/inst2/authorlist-astro'],
        },
        "inst2-physics": {
          "cite": "Inst2, Some Place, City, Country",
          "city": "City",
          "collabs": [
            "icecube",
          ],
          "name": "Inst2 Physics",
          "keycloak_groups": ['/experiments/IceCube/inst2/authorlist-physics'],
        },
    },
    'thanks': {
        'thanks1': 'Thanks1',
        'thanks2': 'Thanks2',
    },
    'acknowledgements': [
        {
            'from': '2020-01-01',
            'to': '',
            'value': 'Big acknowledgement!',
        },
    ],
}

KEYCLOAK_DATA = {
    'users': {
        'jdoe': {
            'firstName': 'John',
            'lastName': 'Doe',
            'username': 'jdoe',
            'email': 'jdoe@icecube.wisc.edu',
            'attributes': {
                'author_email': 'j.doe@icecube.wisc.edu',
                'authorlist_icecube_thanks': 'thanks1',
            },
        },
        'jdoe2': {
            'firstName': 'John2',
            'lastName': 'Doe',
            'username': 'jdoe2',
            'email': 'jdoe2@icecube.wisc.edu',
            'attributes': {
                'authorlist_icecube_thanks': 'thanks2',
            },
        },
    },
    'groups': {
        '/experiments/IceCube/inst1/authorlist': ['jdoe'],
        '/experiments/IceCube/inst2/authorlist-astro': ['jdoe2'],
        '/experiments/IceCube/inst2/authorlist-physics': [],
    }
}

class IceCubeClass:
    authorlist_insts_to_groups = {
        'inst1': '/experiments/IceCube/inst1/authorlist',
        'inst2-astro': '/experiments/IceCube/inst2/authorlist-astro',
        'inst2-physics': '/experiments/IceCube/inst2/authorlist-physics',
    }
    groups_to_authorlist_insts = {v: k for k,v in authorlist_insts_to_groups.items()}


@pytest.mark.parametrize('inst', ['inst1', 'inst2-astro'])
@pytest.mark.asyncio
async def test_match_users(keycloak_fake, inst):
    user_info, get_group_membership, list_insts = keycloak_fake

    get_group_membership.return_value = KEYCLOAK_DATA['groups'][IceCubeClass.authorlist_insts_to_groups[inst]]
    def get_user(username, **kwargs):
        if username in KEYCLOAK_DATA['users']:
            return KEYCLOAK_DATA['users'][username]
        else:
            raise Exception('bad username')
    user_info.side_effect = get_user

    users = await import_from_keycloak.get_keycloak_users('/foo/bar')
    authors = AUTHOR_DATA['authors']

    logging.debug('inst %r', inst)
    logging.debug('authors %r', authors)
    logging.debug('users %r', users)
    ret = import_from_keycloak.match_users(authors, users)
    if inst == 'inst1':
        assert ret == [(authors[0], users[0])]
    elif inst == 'inst2-astro':
        assert ret == [(authors[1], users[0])]
    else:
        assert False


@pytest.mark.asyncio
async def test_match_users_new(keycloak_fake):
    user_info, get_group_membership, list_insts = keycloak_fake

    inst = 'inst1'
    kd = deepcopy(KEYCLOAK_DATA)
    kd['users']['fbar'] = {
        'firstName': 'Foo',
        'lastName': 'Bar',
        'username': 'fbar',
        'email': 'fbar@icecube.wisc.edu',
        'attributes': {},
    }
    kd['groups']['/experiments/IceCube/inst1/authorlist'].append('fbar')

    get_group_membership.return_value = KEYCLOAK_DATA['groups'][IceCubeClass.authorlist_insts_to_groups[inst]]
    def get_user(username, **kwargs):
        if username in kd['users']:
            return kd['users'][username]
        else:
            raise Exception('bad username')
    user_info.side_effect = get_user

    users = await import_from_keycloak.get_keycloak_users('/foo/bar')
    authors = AUTHOR_DATA['authors']

    logging.debug('inst %r', inst)
    logging.debug('authors %r', authors)
    logging.debug('users %r', users)
    ret = import_from_keycloak.match_users(authors, users)
    assert ret == [(authors[0], users[0])]


def test_create_inst_bad_subpath():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {}
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist-astro'

    with pytest.raises(Exception, match='cannot load authorlist'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_bad_mainpath():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {}
        },
    }
    krs_path = '/experiments/IceCube/inst2/authorlist'

    with pytest.raises(KeyError):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_no_authorlist():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'false',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    with pytest.raises(Exception, match='must define a citation'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_no_cite():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    with pytest.raises(Exception, match='must define a citation'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_two_cites():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
            'cite': 'Bar',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    with pytest.raises(Exception, match='differing citations'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_no_city():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    with pytest.raises(Exception, match='must define a city'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_two_cities():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
            'city': 'Foo',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
            'city': 'Bar',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    with pytest.raises(Exception, match='differing cities'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')


def test_create_inst_single():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
            'city': 'Bar',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Foo'
    assert ret['city'] == 'Bar'
    assert ret['collabs'] == ['icecube']
    assert ret['keycloak_groups'] == [krs_path]


def test_create_inst_two_exps():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
            'city': 'Bar',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Foo'
    assert ret['city'] == 'Bar'
    assert ret['collabs'] == ['icecube', 'icecube-gen2']
    assert ret['keycloak_groups'] == [f'{path}/authorlist' for path in krs_groups]


def test_create_inst_skip_exp():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
            'city': 'Bar',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'false',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Foo'
    assert ret['city'] == 'Bar'
    assert ret['collabs'] == ['icecube']
    assert ret['keycloak_groups'] == [krs_path]


def test_create_inst_sublists():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': 'Foo',
                'physics': 'Bar',
            },
            'city': 'Baz',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist-physics'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Bar'
    assert ret['city'] == 'Baz'
    assert ret['collabs'] == ['icecube']
    assert ret['keycloak_groups'] == [krs_path]


def test_create_inst_two_sublists():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': 'Foo',
                'physics': 'Bar',
            },
            'city': 'Baz',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': '',
                'physics': '',
            },
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist-physics'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Bar'
    assert ret['city'] == 'Baz'
    assert ret['collabs'] == ['icecube', 'icecube-gen2']
    assert ret['keycloak_groups'] == [f'{path}/authorlist-physics' for path in krs_groups]


def test_create_inst_sublists_skip():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': 'Foo',
                'physics': 'Bar',
            },
            'city': 'Baz',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
        },
    }
    krs_path = '/experiments/IceCube/inst1/authorlist-physics'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Bar'
    assert ret['city'] == 'Baz'
    assert ret['collabs'] == ['icecube']
    assert ret['keycloak_groups'] == [krs_path]


def test_create_inst_sublists_skip2_missing_cite():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': 'Foo',
                'physics': 'Bar',
            },
            'city': 'Baz',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
        },
    }
    krs_path = '/experiments/IceCube-Gen2/inst1/authorlist'

    with pytest.raises(Exception, match='must define a citation'):
        import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube-Gen2')
    

def test_create_inst_sublists_skip2():
    krs_groups = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
            'authorlists': {
                'astro': 'Foo',
                'physics': 'Bar',
            },
            'city': 'Baz',
        },
        '/experiments/IceCube-Gen2/inst1': {
            'authorlist': 'true',
            'cite': 'Foo',
            'city': 'Blah',
        },
    }
    krs_path = '/experiments/IceCube-Gen2/inst1/authorlist'

    ret = import_from_keycloak.create_inst(krs_groups, krs_path, 'IceCube-Gen2')
    assert ret['name'] == 'inst1'
    assert ret['cite'] == 'Foo'
    assert ret['city'] == 'Blah'
    assert ret['collabs'] == ['icecube-gen2']
    assert ret['keycloak_groups'] == [krs_path]


##################
#
# Test main sync
#
##################


@pytest.mark.skip(reason="this test is old, and should be removed")
@pytest.mark.asyncio
async def test_sync_old(json_file, keycloak_fake, monkeypatch):
    user_info, get_group_membership, list_insts = keycloak_fake

    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    filename_out = filename.parent / 'sync_out.json'

    kd = deepcopy(KEYCLOAK_DATA)
    def members(group, **kwargs):
         return kd['groups'][group]
    get_group_membership.side_effect = members
    def get_user(username, **kwargs):
        if username in kd['users']:
            return kd['users'][username]
        else:
            raise Exception('bad username')
    user_info.side_effect = get_user
    list_insts.return_value = {
        'inst1': {
            'authorlist': 'true',
        },
        'inst2': {
            'authorlist': 'true',
            'authorlists': ['astro', 'physics'],
        },
    }

    monkeypatch.setattr(import_from_keycloak, 'IceCube', IceCubeClass)

    start = filename.open().read()
    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')
    end = filename_out.open().read()

    assert start == end
    
    kd['users']['fbar'] = {
        'firstName': 'Foo',
        'lastName': 'Bar',
        'username': 'fbar',
        'email': 'fbar@icecube.wisc.edu',
        'attributes': {},
    }
    kd['groups']['inst1/authorlist'].append('fbar')
    
    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')
    end = filename_out.open().read()

    assert start != end

    today = datetime.utcnow().date().isoformat()
    ret = s.authors(today)
    expected  = AUTHOR_DATA['authors']
    expected.insert(0, {
      "authname": "F. Bar",
      "collab": "icecube",
      "email": "fbar@icecube.wisc.edu",
      "first": "Foo",
      "from": today,
      "instnames": [
        "inst1"
      ],
      "keycloak_username": "fbar",
      "last": "Bar",
      "orcid": "",
      "thanks": [],
      "to": ""
    })
    assert ret == expected


@pytest.mark.asyncio
async def test_sync(json_file, keycloak_fake, monkeypatch):
    user_info, get_group_membership, list_insts = keycloak_fake

    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    filename_out = filename.parent / 'sync_out.json'

    kd = deepcopy(KEYCLOAK_DATA)
    def members(group, **kwargs):
         return kd['groups'][group]
    get_group_membership.side_effect = members
    def get_user(username, **kwargs):
        if username in kd['users']:
            return kd['users'][username]
        else:
            raise Exception('bad username')
    user_info.side_effect = get_user
    list_insts.return_value = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
        },
        '/experiments/IceCube/inst2': {
            'authorlist': 'true',
            'authorlists': ['astro', 'physics'],
        },
    }

    start = filename.open().read()
    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')
    end = filename_out.open().read()

    assert start == end
    
    kd['users']['fbar'] = {
        'firstName': 'Foo',
        'lastName': 'Bar',
        'username': 'fbar',
        'email': 'fbar@icecube.wisc.edu',
        'attributes': {},
    }
    kd['groups']['/experiments/IceCube/inst1/authorlist'].append('fbar')
    
    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')
    end = filename_out.open().read()

    assert start != end

    today = datetime.utcnow().date().isoformat()
    ret = s.authors(today)
    expected  = AUTHOR_DATA['authors']
    expected.insert(0, {
      "authname": "F. Bar",
      "collab": "icecube",
      "email": "fbar@icecube.wisc.edu",
      "first": "Foo",
      "from": today,
      "instnames": [
        "inst1"
      ],
      "keycloak_username": "fbar",
      "last": "Bar",
      "orcid": "",
      "thanks": [],
      "to": ""
    })
    assert ret == expected

@pytest.mark.asyncio
async def test_sync_new_inst(json_file, keycloak_fake, monkeypatch):
    user_info, get_group_membership, list_insts = keycloak_fake

    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    filename_out = filename.parent / 'sync_out.json'

    kd = deepcopy(KEYCLOAK_DATA)
    kd['users']['fbar'] = {
        'firstName': 'Foo',
        'lastName': 'Bar',
        'username': 'fbar',
        'email': 'fbar@icecube.wisc.edu',
        'attributes': {},
    }
    kd['groups']['/experiments/IceCube/inst3/authorlist'] = ['fbar']
    def members(group, **kwargs):
         return kd['groups'][group]
    get_group_membership.side_effect = members
    def get_user(username, **kwargs):
        if username in kd['users']:
            return kd['users'][username]
        else:
            raise Exception('bad username:'+username)
    user_info.side_effect = get_user
    list_insts.return_value = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
        },
        '/experiments/IceCube/inst2': {
            'authorlist': 'true',
            'authorlists': ['astro', 'physics'],
        },
        '/experiments/IceCube/inst3': {
            'authorlist': 'true',
            'cite': 'My Citation',
            'city': 'City',
        }
    }

    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')

    for instname, values in s._institutions.items():
        if '/experiments/IceCube/inst3/authorlist' in values.get('keycloak_groups', []):
            break
    else:
        logging.debug('%r', s._institutions)
        assert False  #: inst3 was not added


@pytest.mark.asyncio
async def test_sync_new_inst2(json_file, keycloak_fake, monkeypatch):
    user_info, get_group_membership, list_insts = keycloak_fake

    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    filename_out = filename.parent / 'sync_out.json'

    kd = deepcopy(KEYCLOAK_DATA)
    kd['users']['fbar'] = {
        'firstName': 'Foo',
        'lastName': 'Bar',
        'username': 'fbar',
        'email': 'fbar@icecube.wisc.edu',
        'attributes': {},
    }
    kd['groups']['/experiments/IceCube/inst3/authorlist'] = ['fbar']
    def members(group, **kwargs):
         return kd['groups'][group]
    get_group_membership.side_effect = members
    def get_user(username, **kwargs):
        if username in kd['users']:
            return kd['users'][username]
        else:
            raise Exception('bad username:'+username)
    user_info.side_effect = get_user
    list_insts.return_value = {
        '/experiments/IceCube/inst1': {
            'authorlist': 'true',
        },
        '/experiments/IceCube/inst2': {
            'authorlist': 'true',
            'authorlists': ['astro', 'physics'],
        },
        '/experiments/IceCube/inst3': {
            'authorlist': 'true',
            'cite': 'My Citation',
            'city': 'City',
        },
        '/experiments/IceCube-Gen2/inst3': {
            'authorlist': 'true',
        }
    }

    await import_from_keycloak.sync(s, str(filename_out), experiment='IceCube')

    for instname, values in s._institutions.items():
        if '/experiments/IceCube/inst3/authorlist' in values.get('keycloak_groups', []):
            break
    else:
        logging.debug('%r', s._institutions)
        assert False  #: inst3 was not added

    for instname, values in s._institutions.items():
        if '/experiments/IceCube-Gen2/inst3/authorlist' in values.get('keycloak_groups', []):
            break
    else:
        logging.debug('%r', s._institutions)
        assert False  #: inst3 gen2 was not added
    
