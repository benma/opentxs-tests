import pytest
from pyopentxs import (server, ReturnValueError, is_message_success, error, instrument)
from pyopentxs.nym import Nym
from pyopentxs.asset import Asset
from pyopentxs import account
from datetime import datetime, timedelta
from pyopentxs.instrument import transfer, write
from pyopentxs.tests import data

# def test_check_server_id():
#     nym_id = pyopentxs.create_nym()
#     assert pyopentxs.check_server_id(get_server_id(), nym_id)


@pytest.mark.parametrize("issue_for_other_nym,expect_success", [[True, False], [False, True]])
def test_issue_asset_contract(issue_for_other_nym, expect_success):
    server_id = server.first_id()
    nym = Nym().register(server_id)
    issue_for_nym = Nym().register(server_id) if issue_for_other_nym else nym
    with error.expected(None if expect_success else ReturnValueError):
        Asset().issue(nym, open(data.btc_contract_file), server_id, issue_for_nym=issue_for_nym)


def test_create_account():
    server_id = server.first_id()
    nym = Nym().register(server_id)
    asset = Asset().issue(nym, open(data.btc_contract_file), server_id)
    myacct = account.Account(asset, nym).create()

    accounts = account.get_all_ids()
    assert myacct._id in accounts


def new_cheque(source, target, amount, valid_from=-10000, valid_to=10000, source_nym=None):
    now = datetime.utcnow()
    return instrument.Cheque(
        source.server_id,
        amount,
        now + timedelta(0, valid_from),
        now + timedelta(0, valid_to),
        source,
        source_nym or source.nym,
        "test cheque!",
        target.nym
    )


def new_voucher(source, target, amount, source_nym=None):
    return instrument.Voucher(
        source.server_id, amount, source, source_nym or source.nym, "test cheque!", target.nym)


def new_transfer(source, target, amount):
    return amount


@pytest.fixture()
def prepared_accounts(request):
    accts = data.TransferAccounts()
    accts.initial_balance()
    return accts


class TestGenericTransfer:
    def pytest_generate_tests(self, metafunc):
        transfer_amount_data = [
            #(-10, False),
            (10, True),
            # (200, False),
            # (0, False),
            # (2 ** 63 - 100, False),
            # (2 ** 63 - 1, False),
            # (-(2 ** 63), False),
        ]
        instrument_data = [#new_cheque,
                           new_voucher,
                           # new_transfer
        ]
        metafunc.parametrize("amount,should_pass", argvalues=transfer_amount_data)
        metafunc.parametrize("instrument_constructor", argvalues=instrument_data)

    def test_simple_transfer(self, prepared_accounts, amount, should_pass, instrument_constructor):
        instrument = instrument_constructor(
            prepared_accounts.source, prepared_accounts.target, amount)
        with error.expected(None if should_pass else ReturnValueError):
            transfer(instrument, prepared_accounts.source, prepared_accounts.target)
        if should_pass:
            prepared_accounts.assert_balances(-100, 100 - amount, amount)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)


class TestIssuerGenericTransfer:
    def pytest_generate_tests(self, metafunc):
        transfer_amount_data = [
            # (-10, False),
            # (0, False),
            (10, True),
            # # this is the maximal amount that we can transfer, so issuer balance is INT64_MIN
            # (2 ** 63 - 100, True),
            # # now we transfer so big amount that issuer balance should be INT64_MIN - 1
            # (2 ** 63 - 100 + 1, False),
        ]
        instrument_data = [#new_cheque,
                           new_voucher,
                           # new_transfer
        ]
        metafunc.parametrize("amount,should_pass", argvalues=transfer_amount_data)
        metafunc.parametrize("instrument_constructor", argvalues=instrument_data)

    def test_simple_transfer(self, prepared_accounts, amount, should_pass, instrument_constructor):
        instrument = instrument_constructor(
            prepared_accounts.issuer, prepared_accounts.target, amount)
        with error.expected(None if should_pass else ReturnValueError):
            transfer(instrument, prepared_accounts.issuer, prepared_accounts.target)
        if should_pass:
            prepared_accounts.assert_balances(-100 - amount, 100, amount)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)


@pytest.mark.parametrize("instrument_constructor", [new_cheque, new_voucher])
def test_not_account_owner(prepared_accounts, instrument_constructor):
    '''Test that we get a graceful failure when we try to deposit an
       instrument for an account we don't own'''

    instrument = instrument_constructor(
        prepared_accounts.source, prepared_accounts.target, 50,
        source_nym=prepared_accounts.target.nym)
    with error.expected(ReturnValueError):
        transfer(instrument, prepared_accounts.source, prepared_accounts.target)


@pytest.mark.parametrize("instrument_constructor",
                         [new_cheque,

                          pytest.mark.skipif(
                              True,
                              reason="https://github.com/Open-Transactions/opentxs/issues/324")
                          ((new_voucher,)),

                          new_transfer])
def test_wrong_asset_type(instrument_constructor):
    '''Try to transfer eg a cheque from one asset account to another of a
       different type. Should fail'''
    ta_asset1 = data.TransferAccounts().initial_balance()
    ta_asset2 = data.TransferAccounts().initial_balance()
    source = ta_asset1.source
    target = ta_asset2.target
    instrument = instrument_constructor(source, target, 50)
    with error.expected(ReturnValueError):
        transfer(instrument, source, target)
    ta_asset2.assert_balances(-100, 100, 0)


@pytest.mark.parametrize("instrument_constructor",
                         [new_cheque, new_voucher])
def test_cancel_instrument(instrument_constructor):
    '''Cancel an instrument and make sure it can't be deposited.'''
    accounts = data.TransferAccounts().initial_balance()
    instrument = instrument_constructor(accounts.source, accounts.target, 50)
    write(instrument)
    instrument.cancel()
    with error.expected(ReturnValueError):
        instrument.deposit(accounts.target.nym, accounts.target)
    accounts.assert_balances(-100, 100, 0)


class TestChequeTransfer:
    @pytest.mark.parametrize("amount,first_valid,later_income,second_valid", [
        # not enough funds
        (200, False, 100, True),
        (200, False, 50, False),
        # cheque can be used only once
        (10, True, 0, False),
        (10, True, 1, False),
    ])
    def test_deposit_twice(self, prepared_accounts, amount, first_valid, later_income,
                           second_valid):
        # create cheque and try to deposit it
        cheque = new_cheque(prepared_accounts.source, prepared_accounts.target, amount)
        with error.expected(None if first_valid else ReturnValueError):
            transfer(cheque, prepared_accounts.source, prepared_accounts.target)

        expected_source = 100
        expected_target = 0
        if (first_valid):
            expected_source -= amount
            expected_target += amount
        prepared_accounts.assert_balances(-100, expected_source, expected_target)

        # now transfer more funds to source
        if later_income != 0:
            income = new_cheque(prepared_accounts.issuer, prepared_accounts.source, later_income)
            transfer(income, prepared_accounts.issuer, prepared_accounts.source)
        expected_source += later_income

        # and repeat cheque deposit
        with error.expected(None if second_valid else ReturnValueError):
            deposit = cheque.deposit(prepared_accounts.target.nym, prepared_accounts.target)
        if second_valid:
            expected_source -= amount
            expected_target += amount
            assert is_message_success(deposit)

        prepared_accounts.assert_balances(-100 - later_income, expected_source, expected_target)

    @pytest.mark.parametrize("valid_from,valid_to,valid", [
        # valid cheque
        (-100, 100, True),
        # cheque is expired
        (-100, -50, False),
        # not yet valid
        (500, 100, False),
        # incorrect intervals
        (-100, -200, False),
        (100, -100, False),
        (200, 100, False),
    ])
    def test_expired_cheque(self, prepared_accounts, valid_from, valid_to, valid):
        with error.expected(None if valid else ReturnValueError):
            transfer(new_cheque(prepared_accounts.source, prepared_accounts.target, 10,
                                valid_from, valid_to),
                     prepared_accounts.source,
                     prepared_accounts.target)
        if valid:
            prepared_accounts.assert_balances(-100, 90, 10)
        else:
            prepared_accounts.assert_balances(-100, 100, 0)
