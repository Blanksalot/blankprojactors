import pytest
import subprocess
import requests
import time

SERVER_BIN = "twtask"


@pytest.fixture
def player_server():
    sp = subprocess.Popen(['./'+SERVER_BIN], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    time.sleep(1)
    yield sp
    subprocess.Popen(['kill', '-9', str(sp.pid)]).communicate()
    sp.communicate()


@pytest.fixture
def kill_player_server(player_server):
    def foo():
        subprocess.Popen(['kill', '-9', str(player_server.pid)]).communicate()
        player_server.communicate()
    return foo


@pytest.fixture
def restart_server(kill_player_server):
    def foo(pid):
        kill_player_server(pid)
        sp = subprocess.Popen(['./' + SERVER_BIN], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        return sp.pid
    return foo

@pytest.fixture
def raw_query(player_server, page, user, password):
    return requests.get('http://localhost:8000/players?page={}'.format(page), auth=(user, password))

@pytest.fixture
def query_func(player_server):
    def foo(page=1, user="admin", password="admin", port=8000):
        return requests.get('http://localhost:{0}/players?page={1}'.format(port, page), auth=(user, password))
    return foo


@pytest.fixture
def query(player_server):
    def foo(page):
        r = requests.get('http://localhost:8000/players?page={}'.format(page), auth=('admin', 'admin'))
        assert r.status_code == 200, "http get failed for page={}".format(page)
        return r.json()
    return foo


@pytest.fixture
def reliable_query(player_server, query):
    def foo(page):
        bad_data = []
        data = query(page)
        for i, item in enumerate(data):
            if not item["Name"]:
                bad_data.append(i)
        while bad_data:
            new_data = query(page)
            for i in bad_data:
                if new_data[i]["Name"]:
                    data[i]["Name"] = new_data[i]["Name"]
                    bad_data.remove(i)
        return data
    return foo


@pytest.fixture
def unreliable_query(player_server, query):
    def foo(page=1, timeout=15):
        data = []
        start = time.time()
        while time.time() - start < timeout:
            new_data = query(page)
            for i in new_data:
                if not i["Name"]:
                    data = new_data
                    break
            time.sleep(1)
        if not data:
            raise TimeoutError("No corrupt data within {} seconds".format(timeout))
        return data
    return foo


@pytest.fixture()
def post_query(player_server):
    def foo(page=1):
        return requests.post('http://localhost:8000/players?page={}'.format(page), auth=('admin', 'admin'))
    return foo


@pytest.fixture
def result_syntax_verifier():
    def foo(result):
        for i, result_instance in enumerate(result):
            condition = hasattr(result_instance, "Name") and hasattr(result_instance, "ID")
            assert condition, "field {0} has bad syntax {1}".format(i, result_instance)
    return foo

@pytest.fixture
def result_name_field_verifier(result_syntax_verifier):
    def foo(result):
        result_syntax_verifier(result)
        bad_ids = []
        for result_instance in result:
            if not result_instance["Name"]:
                bad_ids.append(result_instance['ID'])
        assert not bad_ids, "some ids have no name: {}".format(bad_ids)
    return foo


@pytest.fixture
def id_continuation_verifier():
    def foo(result1, result2, page):
        condition = result1[-1]['ID'] + 1 == result2[0]['ID']
        assert condition, "ids not continuous between pages: {0} - {1}".format(page, page+1)
    return foo


@pytest.fixture
def unique_id_to_player_match_verifier():
    def foo(list_to_check):
        book = {}
        for item in list_to_check:
            if item['Name'] in book:
                book[item['Name']].append(item['ID'])
            else:
                book[item['Name']] = [item['ID']]
        bad_players = {}
        for name in book:
            if len(book[name]) > 1:
                bad_players[name] = book[name]
        if bad_players:
            print(list_to_check)
        assert not bad_players, "{}".format(bad_players)
    return foo
