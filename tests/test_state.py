import json
import pytest

from authorlist.state import State


def test_init(json_file):
    filename = json_file({
        'authors': 'AUTHORS',
        'institutions': 'INSTS',
        'thanks': 'THANKS',
        'acknowledgements': 'ACKS',
    })

    s = State(filename)
    assert s._authors == 'AUTHORS'
    assert s._institutions == 'INSTS'
    assert s._thanks == 'THANKS'
    assert s._acknowledgements == 'ACKS'


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
    ],
    'institutions': {
        "inst1": {
          "cite": "Inst1, Some Place, City, Country",
          "city": "City",
          "collabs": [
            "icecube",
          ],
          "name": "Inst1"
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


def test_authors(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    authors = s.authors('2020-01-01')
    assert authors == AUTHOR_DATA['authors']

    authors = s.authors('2019-01-01')
    assert authors == []


def test_remove_author(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    s.remove_author(s._authors[0])

    assert s.authors('2020-01-01') == []


def test_add_author(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    new_author = {
      "authname": "J. Doe",
      "collab": "icecube",
      "email": "jane.doe@icecube.wisc.edu",
      "first": "Jane",
      "from": "2020-02-01",
      "instnames": [
        "inst1"
      ],
      "keycloak_username": "jane",
      "last": "Doe",
      "orcid": "",
      "thanks": [],
      "to": ""
    }
    s.add_author(new_author)

    assert s.authors('2020-01-01') == AUTHOR_DATA['authors']

    authors = s.authors('2020-02-01')
    assert authors == [AUTHOR_DATA['authors'][0], new_author]


def test_update_authors(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    
    assert s.authors('2021-01-02') == AUTHOR_DATA['authors']

    author = s._authors[0].copy()
    author['to'] = '2021-01-01'

    new_author = {
      "authname": "J. Doe",
      "collab": "icecube",
      "email": "j.doe@icecube.wisc.edu",
      "first": "John",
      "from": "2019-01-01",
      "instnames": [
        "inst1"
      ],
      "keycloak_username": "jdoe",
      "last": "Doe",
      "orcid": "0000-0001-0002-0003",
      "thanks": ['thanks1'],
      "to": "2019-12-31"
    }
    s._authors.insert(0, new_author)

    s.update_authors([author])

    assert s.authors('2019-01-02') == [new_author]
    assert s.authors('2020-01-02') == [author]
    assert s.authors('2021-01-02') == []


def test_update_most_recent_author(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    
    assert s.authors('2021-01-02') == AUTHOR_DATA['authors']

    author = s._authors[0].copy()
    author['to'] = '2021-01-01'
    s.update_authors([author])

    assert s.authors('2021-01-02') == []


def test_save(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)
    
    author = s._authors[0].copy()
    author['to'] = '2021-01-01'
    s.update_authors([author])
    s.save(filename)

    with open(filename) as f:
        data = json.load(f)
    assert data['authors'] == [author]


def test_insts(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    insts = s.institutions('2020-01-01')
    assert insts == AUTHOR_DATA['institutions']

    insts = s.institutions('2019-01-01')
    assert insts == {}


def test_add_inst(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    insts = s.institutions('2020-01-01')
    assert insts == AUTHOR_DATA['institutions']

    args = {
        'name': 'inst2',
        'collabs': ['icecube'],
        'cite': 'foo bar',
        'city': 'My City',
    }
    inst_key = s.add_institution(**args)

    assert inst_key.startswith('inst2')

    insts = s.institutions('2020-01-01')
    assert insts == AUTHOR_DATA['institutions']

    # now add author for that inst
    new_author = {
      "authname": "J. Doe",
      "collab": "icecube",
      "email": "jane.doe@icecube.wisc.edu",
      "first": "Jane",
      "from": "2020-01-01",
      "instnames": [
        inst_key
      ],
      "keycloak_username": "jane",
      "last": "Doe",
      "orcid": "",
      "thanks": [],
      "to": ""
    }
    s.add_author(new_author)
    
    insts = s.institutions('2020-01-01')
    expected = list(AUTHOR_DATA['institutions'])
    expected.append(inst_key)
    assert list(insts) == expected
    assert insts[inst_key] == args

    # now add a dup inst
    inst_key2 = s.add_institution(**args)
    assert inst_key != inst_key2
    assert inst_key2.startswith('inst2')
    assert inst_key2.endswith('-2')

    # now add a unicode inst
    args = {
        'name': 'Argüelle\'s Inst',
        'collabs': ['icecube'],
        'cite': 'foo bar',
        'city': 'My City',
    }
    inst_key3 = s.add_institution(**args)
    assert inst_key3.startswith('arguelles-inst')

    # check that name is still unicode in output
    new_author = {
      "authname": "J. Doe",
      "collab": "icecube",
      "email": "jane.doe2@icecube.wisc.edu",
      "first": "Jane",
      "from": "2020-01-01",
      "instnames": [
        inst_key3
      ],
      "keycloak_username": "jane2",
      "last": "Doe",
      "orcid": "",
      "thanks": [],
      "to": ""
    }
    s.add_author(new_author)
    insts = s.institutions('2020-01-01')
    assert insts[inst_key3] == args


def test_lookup_insts(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    insts = s.institutions('2020-01-01')
    assert insts == AUTHOR_DATA['institutions']

    args = {
        'name': 'inst2',
        'collabs': ['icecube'],
        'cite': 'foo bar',
        'city': 'My City',
    }
    inst_key = s.add_institution(**args)

    ret = s.lookup_institutions(city='My City')
    expected = {inst_key: args}
    assert ret == expected

    ret = s.lookup_institutions(collabs=['icecube'])
    assert len(ret) == 2

    ret = s.lookup_institutions(foo='bar')
    assert not ret


def test_thanks(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    thanks = s.thanks('2020-01-01')
    assert thanks == {'thanks1': 'Thanks1'}

    thanks = s.thanks('2019-01-01')
    assert thanks == {}


def test_acks(json_file):
    filename = json_file(AUTHOR_DATA)
    s = State(filename)

    acks = s.acknowledgements('2020-01-01')
    assert acks == [x['value'] for x in AUTHOR_DATA['acknowledgements']]

    acks = s.acknowledgements('2019-01-01')
    assert acks == []
