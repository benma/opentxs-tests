from pyopentxs.nym import Nym
from pyopentxs.tests import data
from pyopentxs import error, ReturnValueError
import pytest


def test_register_nym():
    Nym().register()


def test_delete_nym():
    Nym().register().delete()


def test_reregister_nym():
    n = Nym().register()
    n.delete()
    n.register()


def test_double_delete():
    n = Nym().register()
    n.delete()
    with error.expected(ReturnValueError):
        n.delete()

string_overflow = lambda: "asdfasdf" * 1024
string_returnchar = lambda: "\n"


@pytest.mark.parametrize(
    "newname",
    ["Bob",
     pytest.mark.skipif(True,
                        reason="https://github.com/Open-Transactions/opentxs/issues/400")(("",)),
     string_returnchar,
     string_overflow,
     "我能吞下玻璃而不伤身体"])
def test_set_name(newname):
    newname = newname() if callable(newname) else newname
    n = Nym().create()
    origname = "Joe"
    n.set_name(origname)
    assert n.get_name() == origname
    n.register()
    n.set_name(newname)
    assert n.get_name() == newname
    n.register()

# server says "(Allowed in order to prevent sync issues) ==> User is
# registering nym that already exists:"
# def test_double_register():
#     '''Should not be able to register the same nym twice on the same server'''
#     n = Nym().register()
#     with error.expected(ReturnValueError):
#         n.register()


@pytest.fixture()
def prepared_accounts(request):
    accts = data.TransferAccounts()
    accts.initial_balance()
    return accts


@pytest.mark.skipif(True, reason="https://github.com/Open-Transactions/opentxs/issues/363")
def test_delete_nonempty_nym(prepared_accounts):
    with error.expected(ReturnValueError):
        prepared_accounts.source.nym.delete()


@pytest.mark.skipif(True, reason="https://github.com/Open-Transactions/opentxs/issues/363")
def test_delete_issuer_nym(prepared_accounts):
    with error.expected(ReturnValueError):
        prepared_accounts.issuer.nym.delete()
