"""Explicitly opt-in hosted policy/transaction tests using ordinary test-user tokens.

These tests append immutable records to TWO dedicated precreated test accounts.
They never apply migrations, create users, send mail or automatically clean history.
Only the separately gated disposable-account test can delete an Auth user.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
from uuid import uuid4

import pytest

from auth_service import AuthConfig, authenticate, logout, ordinary_client, delete_account
from progress_store import GuestProgressStore, analyze, rebuild_bandit, new_rating
from supabase_store import SupabaseProgressStore

pytestmark = [pytest.mark.live, pytest.mark.skipif(os.environ.get('MATHMENTOR_LIVE') != '1', reason='Live Supabase tests require explicit opt-in')]


def required(name):
    value = os.environ.get(name)
    if not value:
        pytest.fail('Missing dedicated live-test configuration: ' + name, pytrace=False)
    return value


@pytest.fixture
def actors():
    config = AuthConfig(required('MM_TEST_SUPABASE_URL'), required('MM_TEST_PUBLISHABLE_KEY'))
    sessions = []
    try:
        for label in ('A', 'B'):
            sessions.append(authenticate(config, required('MM_TEST_EMAIL_' + label), required('MM_TEST_PASSWORD_' + label)))
    except Exception:
        pytest.fail('Dedicated test-account authentication failed; provider details suppressed.', pytrace=False)
    assert sessions[0].user_id != sessions[1].user_id
    yield config, sessions
    for session in sessions:
        logout(session)


@pytest.fixture
def attempt():
    guest = GuestProgressStore({})
    return analyze(guest, 'ALG1-LIN-001', ['2*x + 3 = 11', '2*x = 10'], rebuild_bandit(guest))[0]


def assert_denied(action):
    try:
        action()
    except Exception:
        return
    pytest.fail('Expected database rejection did not occur.', pytrace=False)


def test_live_atomic_batch_retry_conflict_and_feedback(actors, attempt):
    _, (session, other) = actors
    store = SupabaseProgressStore(session)
    bad = deepcopy(attempt)
    bad['attempt_id'] = str(uuid4())
    bad['evaluations'][0]['confidence'] = 5
    # Bypass Python validation intentionally: this tests the RPC's actual rollback.
    assert_denied(lambda: session.protected(lambda c: c.rpc('save_attempts', {'p_attempts': [attempt, bad]}).execute()))
    ids = {a['attempt_id'] for a in store.load_attempts()}
    assert attempt['attempt_id'] not in ids and bad['attempt_id'] not in ids
    store.save_attempts([attempt])
    store.save_attempts([attempt])
    assert sum(a['attempt_id'] == attempt['attempt_id'] for a in store.load_attempts()) == 1
    conflict = {**attempt, 'overall_score': 99.9}
    assert_denied(lambda: session.protected(lambda c: c.rpc('save_attempts', {'p_attempts': [conflict]}).execute()))
    saved = next(a for a in store.load_attempts() if a['attempt_id'] == attempt['attempt_id'])
    assert saved == attempt
    step = attempt['evaluations'][1]
    rating = new_rating(step, step['feedback_style'], 1)
    assert store.record_feedback(attempt['attempt_id'], rating)
    assert not store.record_feedback(attempt['attempt_id'], {**rating, 'feedback_event_id': str(uuid4()), 'reward': -1})
    events = [r for r in store.load_feedback_events() if r['attempt_id'] == attempt['attempt_id']]
    assert len(events) == 1 and events[0]['reward'] == 1
    assert not any(a['attempt_id'] == attempt['attempt_id'] for a in SupabaseProgressStore(other).load_attempts())


def test_live_cross_owner_children_forged_ownership_and_immutable_columns(actors, attempt):
    config, (a, b) = actors
    SupabaseProgressStore(a).save_attempts([attempt])
    aid = attempt['attempt_id']
    rating = new_rating(attempt['evaluations'][1], 'socratic', 1)
    assert_denied(lambda: SupabaseProgressStore(b).record_feedback(aid, rating))
    assert_denied(lambda: b.protected(lambda c: c.rpc('save_attempts', {'p_attempts': [{**attempt, 'user_id': a.user_id}]}).execute()))
    assert_denied(lambda: b.protected(lambda c: c.rpc('save_attempts', {'p_attempts': [attempt]}).execute()))
    step = {**attempt['evaluations'][0], 'attempt_id': aid, 'user_id': b.user_id, 'student_step_index': 99}
    assert_denied(lambda: b.protected(lambda c: c.table('step_evaluations').insert(step).execute()))
    forged_rating = {**rating, 'attempt_id': aid, 'user_id': b.user_id}
    assert_denied(lambda: b.protected(lambda c: c.table('feedback_events').insert(forged_rating).execute()))
    assert_denied(lambda: a.protected(lambda c: c.table('profiles').update({'created_at': '2000-01-01T00:00:00Z'}).eq('user_id', a.user_id).execute()))
    assert_denied(lambda: a.protected(lambda c: c.table('profiles').update({'user_id': b.user_id}).eq('user_id', a.user_id).execute()))
    assert_denied(lambda: a.protected(lambda c: c.table('attempts').update({'overall_score': 0}).eq('attempt_id', aid).execute()))
    assert_denied(lambda: a.protected(lambda c: c.table('attempts').delete().eq('attempt_id', aid).execute()))
    public = ordinary_client(config)
    for table in ('profiles', 'attempts', 'step_evaluations', 'feedback_events'):
        assert_denied(lambda table=table: public.table(table).select('*').execute())


def test_live_import_atomicity_pagination_and_concurrent_retries(actors, attempt):
    config, (a, _) = actors
    other_session = authenticate(config, required('MM_TEST_EMAIL_A'), required('MM_TEST_PASSWORD_A'))
    batch = []
    for _ in range(3):
        item = deepcopy(attempt)
        item['attempt_id'] = str(uuid4())
        step = item['evaluations'][1]
        item['ratings'] = [new_rating(step, step['feedback_style'], 1)]
        batch.append(item)
    invalid = deepcopy(batch[-1])
    invalid['ratings'][0]['student_step_index'] = 999
    assert_denied(lambda: a.protected(lambda c: c.rpc('save_attempts', {'p_attempts': batch[:2]+[invalid]}).execute()))
    assert not {i['attempt_id'] for i in batch} & {i['attempt_id'] for i in SupabaseProgressStore(a).load_attempts()}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(SupabaseProgressStore(s).save_attempts, batch) for s in (a, other_session)]
            for job in jobs:
                job.result()
        store = SupabaseProgressStore(a, page_size=1)
        found = {i['attempt_id']: i for i in store.load_attempts()}
        assert all(found[i['attempt_id']] == i for i in batch)
        assert len([r for r in store.load_feedback_events() if r['attempt_id'] in {i['attempt_id'] for i in batch}]) == 3
    finally:
        logout(other_session)


def test_live_profiles_rename_preserves_owner_and_history(actors, attempt):
    _, (a, b) = actors
    first, second = SupabaseProgressStore(a), SupabaseProgressStore(b)
    old_a, old_b = first.load_profile(), second.load_profile()
    try:
        first.save_attempts([attempt])
        first.save_profile({**old_a, 'display_name': 'Same dedicated test name'})
        second.save_profile({**old_b, 'display_name': 'Same dedicated test name'})
        first.save_profile({**old_a, 'display_name': 'Renamed dedicated test account'})
        assert any(i['attempt_id'] == attempt['attempt_id'] for i in first.load_attempts())
        assert not any(i['attempt_id'] == attempt['attempt_id'] for i in second.load_attempts())
    finally:
        first.save_profile(old_a)
        second.save_profile(old_b)


@pytest.mark.skipif(os.environ.get('MATHMENTOR_DELETE_DISPOSABLE') != '1', reason='Deletion requires a separately designated disposable account and explicit flag')
def test_live_disposable_account_deletion_cascades(attempt):
    config = AuthConfig(required('MM_TEST_SUPABASE_URL'), required('MM_TEST_PUBLISHABLE_KEY'))
    session = authenticate(config, required('MM_DISPOSABLE_EMAIL'), required('MM_DISPOSABLE_PASSWORD'))
    # Extra guard: do not permit deletion of either ordinary test actor.
    assert session.email not in {os.environ.get('MM_TEST_EMAIL_A'), os.environ.get('MM_TEST_EMAIL_B')}
    assert session.user_id == required('MM_DISPOSABLE_USER_ID')
    store = SupabaseProgressStore(session)
    store.save_attempts([attempt])
    store.record_feedback(attempt['attempt_id'], new_rating(attempt['evaluations'][1], 'socratic', 1))
    owner = session.user_id
    # Only the isolated deletion function receives administrator configuration.
    delete_account(session, config, required('MM_DISPOSABLE_PASSWORD'),
                   {'supabase': {'secret_key': required('MM_DISPOSABLE_SECRET_KEY')}})
    for table in ('profiles', 'attempts', 'step_evaluations', 'feedback_events'):
        assert session.client.table(table).select('*').eq('user_id', owner).execute().data == []
