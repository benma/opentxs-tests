#!/usr/bin/env python3
import shutil
import os
import sys
import pytest
import pyopentxs
from pyopentxs import notary
import subprocess


def create_fresh_ot_config():
    # this creates fresh data in ../ot-clean-data/.ot
    if os.path.exists(pyopentxs.config_dir):
        shutil.rmtree(pyopentxs.config_dir)

    # create a client wallet just for making the server contract
    os.system("opentxs --dummy-passphrase changepw")

    # create server contract and empty the client side data
    notary.setup(open('../test-data/sample-contracts/localhost.xml'), total_servers=1)

    # TODO: run goatary here with the correct id!
    
    # p = subprocess.Popen(["notary", "--notary-id=otxEK5JMnP27NJWUkjEeXtupYwaVBKkVRUJU"], stdin=subprocess.PIPE)
    
    # set cron interval to shorter than default
    # config_data = notary.config.read()
    # config_data['cron']['ms_between_cron_beats'] = '2500'  # in milliseconds
    # notary.config.write()


def fresh_setup():
    '''opentxs-notary must be on the PATH'''

    create_fresh_ot_config()
    print("created fresh config, restarting...")
    #notary.restart()
    print("restarted.")
    # wait for ready
    # doesn't seem to be necessary
    # time.sleep(2)


if __name__ == "__main__":
    fresh_setup()
    pytest.main(sys.argv[1:])
    pyopentxs.cleanup()
