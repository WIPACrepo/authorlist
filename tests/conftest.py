import json
import pytest


@pytest.fixture(scope="module")
def json_file(tmp_path_factory):
    tmpdir = tmp_path_factory.mktemp('jsons')
    def json_maker(data):
        filename = tmpdir / 'output.json'
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        return filename
    yield json_maker