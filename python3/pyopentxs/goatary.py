import subprocess
import tempfile
import os
import opentxs
import pyopentxs
from pyopentxs import server

def download(url):
    import urllib.request
    return urllib.request.urlopen(url).read().decode('ascii')

def add_server_contract(contract_dir):
    pyopentxs.init()
    if os.environ.get('DOCKER'):
        # The running notary docker image provides a simple web server to get
        # a valid test contract.
        decoded_signed_contract = download("http://notary:1337/contract.otc")
        server_contract_id = download("http://notary:1337/notaryID").strip()
    else:
        decoded_signed_contract = open(contract_dir + "/contract.otc").read()
        server_contract_id = open(contract_dir + "/notaryID").read().strip()
    opentxs.OTAPI_Wrap_AddServerContract(decoded_signed_contract)
    # should be just one known active server now
    server.active = [server_contract_id]


def create_server_contract():
    '''
       Creates a notary contract, and returns the directory where the
       files were placed.

    '''
    tmpdir = tempfile.mkdtemp()
    p = subprocess.Popen(["create_contract"], cwd=tmpdir)
    p.wait()
    return tmpdir


def start_notary(contract_dir):
    '''Starts a new notary with the given contract_dir (created using
       create_contract tool)'''

    if os.environ.get('DOCKER'):
        # Notary should already be running as a docker image.
        pass
    else:
        pyopentxs.killall("notary")

        # danger, also kill any opentxs-notary,
        # since they occupy the same port
        pyopentxs.killall("opentxs-notary")

        trans_key_arg = "--transport-key=%s/transportKey" % contract_dir
        sign_key_arg = "--signing-key=%s/signingKey" % contract_dir
        notary_id_arg = "--notary-id=`cat %s/notaryID`" % contract_dir
        os.system("notary %s %s %s > opentxs-goatary.log 2>&1 &" %
                  (trans_key_arg, sign_key_arg, notary_id_arg))
