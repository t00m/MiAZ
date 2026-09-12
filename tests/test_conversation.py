"""The documents read as exchanges: grouping, ordering and sides."""

from MiAZ.backend.conversation import (
    Message, concept_key, conversations, exchanges, home_party, is_outgoing, owner_of)
from MiAZ.backend.util import UNKNOWN_DATE


def msg(date, sentby, sentto, concept):
    return Message(date=date, sentby=sentby, sentto=sentto, concept=concept)


def test_concept_key_ignores_case_and_underscores():
    assert concept_key('Car_Insurance') == concept_key('CAR INSURANCE ')


def test_owner_is_the_party_on_most_documents():
    messages = [msg('20240101', 'ME', 'BANK', 'x'),
                msg('20240102', 'INSURER', 'ME', 'y'),
                msg('20240103', 'BANK', 'ME', 'x')]
    assert owner_of(messages) == 'ME'


def test_owner_tie_is_stable():
    messages = [msg('20240101', 'B', 'A', 'x')]
    assert owner_of(messages) == 'A'
    assert owner_of([]) is None


def test_outgoing_is_what_the_owner_sent():
    sent = msg('20240101', 'ME', 'BANK', 'x')
    received = msg('20240102', 'BANK', 'ME', 'x')
    assert is_outgoing(sent, 'ME') is True
    assert is_outgoing(received, 'ME') is False
    assert is_outgoing(sent, None) is False


def test_conversations_group_by_concept_and_read_oldest_first():
    messages = [msg('20240301', 'BANK', 'ME', 'Loan'),
                msg('20240101', 'ME', 'BANK', 'loan'),
                msg('20240201', 'ME', 'INSURER', 'Car_Insurance')]
    result = conversations(messages, titles={'LOAN': 'Loan'})
    assert [c.title for c in result] == ['Loan', 'CAR INSURANCE']
    loan = result[0]
    assert [m.date for m in loan.messages] == ['20240101', '20240301']
    assert loan.first_date == '20240101'
    assert loan.last_date == '20240301'
    assert loan.parties == ['ME', 'BANK']


def test_conversations_newest_activity_first():
    messages = [msg('20200101', 'ME', 'A', 'old'),
                msg('20250101', 'ME', 'B', 'new')]
    assert [c.key for c in conversations(messages)] == ['NEW', 'OLD']


def test_undated_conversations_go_last():
    messages = [msg(UNKNOWN_DATE, 'ME', 'A', 'undated'),
                msg('20200101', 'ME', 'B', 'dated')]
    assert [c.key for c in conversations(messages)] == ['DATED', 'UNDATED']


def test_exchanges_drop_single_documents():
    messages = [msg('20200101', 'ME', 'A', 'alone'),
                msg('20200102', 'ME', 'B', 'pair'),
                msg('20200103', 'B', 'ME', 'pair')]
    assert [c.key for c in exchanges(conversations(messages))] == ['PAIR']


def test_home_party_is_the_owner_when_present():
    convo = conversations([msg('20200101', 'BANK', 'ME', 'x'),
                           msg('20200102', 'ME', 'BANK', 'x')])[0]
    assert home_party(convo, 'ME') == 'ME'


def test_home_party_falls_back_to_who_received_most():
    convo = conversations([msg('20200101', 'LAB', 'KID', 'x'),
                           msg('20200102', 'LAB', 'KID', 'x'),
                           msg('20200103', 'DOC', 'LAB', 'x')])[0]
    assert home_party(convo, 'ME') == 'KID'
