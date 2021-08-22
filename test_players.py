import time
import pytest
import requests
import random
import threading
import subprocess
from requests.auth import HTTPDigestAuth
from player_fixtures import query, result_name_field_verifier, result_syntax_verifier, id_continuation_verifier, \
    unreliable_query, reliable_query, raw_query, player_server, query_func, unique_id_to_player_match_verifier, \
    post_query, timed_query, TimedThread, verify_server_is_up


def test_sanity(query, result_syntax_verifier):
    result_syntax_verifier(query(1))


@pytest.mark.parametrize("page", [1, 5, 10])
def test_simple_query(query, result_name_field_verifier, page):
    result_name_field_verifier(query(page))


@pytest.mark.parametrize("page", [1, 5, 10])
def test_double_query(query, result_name_field_verifier, page):
    res1 = query(page)
    result_name_field_verifier(page, res1)
    res2 = query(page)
    result_name_field_verifier(page, res2)
    assert res1 == res2, "data doesn't match"


@pytest.mark.parametrize("page", [2, 6, 11])
def test_query_subsequent_pages(query, result_name_field_verifier, page):
    result_name_field_verifier(query(page))
    result_name_field_verifier(query(page+1))
    result_name_field_verifier(query(page-1))


@pytest.mark.parametrize("page", [1, 5, 10])
@pytest.mark.bug
def test_data_not_corrupt(unreliable_query, page):
    with pytest.raises(TimeoutError):
        unreliable_query(page)


@pytest.mark.parametrize("page", [1, 5, 10])
@pytest.mark.bug
def test_indices_continuation(query, id_continuation_verifier, page):
    res1 = query(page)
    res2 = query(page+1)
    id_continuation_verifier(res1, res2, page)


@pytest.mark.parametrize("page", [2, 3, 4, 5, 6, 7, 9, 10,11, 12, 13, 14, 15, 16,
                                  pytest.param(1, marks=pytest.mark.bug),
                                  pytest.param(8, marks=pytest.mark.bug)])
def test_player_to_id_match_is_unique(reliable_query, unique_id_to_player_match_verifier, page):
    unique_id_to_player_match_verifier(reliable_query(page))


@pytest.mark.parametrize("page", [1, 5, 10])
def test_server_restart(player_server, restart_server, kill_player_server, reliable_query, page):
    a1 = reliable_query(page)
    pid = player_server
    new_pid = restart_server(pid)
    a2 = reliable_query(page)
    kill_player_server(new_pid)
    assert a1 == a2, "data doesn't match"


@pytest.mark.bug
def test_limits(query_func):
    lower = query_func(0, 'admin', 'admin')
    upper = query_func(18, 'admin', 'admin')
    assert lower.status_code == upper.status_code, "limits don't return consistent status code"


@pytest.mark.parametrize("page, user, password", [(1, '', ''), (1, 'a', 'a'),
                                                  pytest.param(1, 'admin', '', marks=pytest.mark.bug),
                                                  pytest.param(1, '', 'admin', marks=pytest.mark.bug)])
def test_bad_auth(raw_query):
    assert raw_query.status_code == 401, "unexpected status_code({0})".format(raw_query.status_code)


@pytest.mark.parametrize("page, user, password", [('"1"', 'admin', 'admin'),
                                                  (1.001, 'admin', 'admin)'),
                                                  (-1, 'admin', 'admin')])
def test_bad_value_for_page(raw_query):
    assert raw_query.status_code == 418, "unexpected status_code({0})".format(raw_query.status_code)


def test_correct_and_incorrect_auths(query_func):
    r = query_func(1, "admin", "admin")
    assert r.status_code == 200, "unexpected status_code({0})".format(r.status_code)
    r = query_func(1, "a", "a")
    assert r.status_code == 401, "unexpected status_code({0})".format(r.status_code)
    r = query_func(1, "admin", "admin")
    assert r.status_code == 200, "unexpected status_code({0})".format(r.status_code)


def test_digest_auth():
    r = requests.get('http://localhost:8000/players?page=1', auth=HTTPDigestAuth('admin', 'admin'))
    assert r.status_code == 401, "unexpected status_code({0}) for unsupported HTTPDigestAuth".format(r.status_code)


def test_query_non_existent_api():
    r = requests.get('http://localhost:8000/players2?page=1', auth=('admin', 'admin'))
    assert r.status_code == 404, "unexpected status_code({0})".format(r.status_code)


def test_bad_port():
    with pytest.raises(requests.exceptions.ConnectionError):
        requests.get('http://localhost:8001/players?page=1', auth=('admin', 'admin'))


@pytest.mark.parametrize("page", [1])
def test_stress_same_query(query, page):
    for i in range(10000):
        query(page)


def test_subsequent_query(query):
    for i in range(20000):
        ind = i % 16 + 1
        query(ind)


def test_stress_random_query(query):
    for i in range(10000):
        query(random.randrange(1, 16))


@pytest.mark.parametrize("page", [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 16,
                                  pytest.param(7, marks=pytest.mark.bug),
                                  pytest.param(8, marks=pytest.mark.bug)])
def test_performance(query, page):
    st = time.time()
    query(page)
    exec_time = time.time() - st
    print(page, "-", exec_time, "sec")
    assert exec_time < 1, "{0} - {1} sec is too long ".format(page, exec_time)


@pytest.mark.bug
def test_post(post_query):
    r = post_query(1)
    assert r.status_code == 405, 'POST is not returning expected status code'


@pytest.mark.bug
@pytest.mark.parametrize("page1, page2", [(1, 1), (1, 2)])
def test_multiple_clients(timed_query, verify_server_is_up, page1, page2):
    t1 = TimedThread(1, page1, 10000, timed_query)
    t2 = TimedThread(2, page2, 10000, timed_query)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    verify_server_is_up()

