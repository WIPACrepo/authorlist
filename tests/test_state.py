import json
import pytest

from authorlist.state import State


@pytest.fixture(scope="module")
def json_file(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp('jsons')
    def json_maker(data):
        filename = tmpdir / 'output.json'
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        return filename
    yield json_maker


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
