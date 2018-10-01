import subprocess
from webservice.server import application
from time import sleep
import pytest


@pytest.fixture(scope="session")
def soap_service():

    # with ThreadPoolExecutor(max_workers=2) as executor:
    #     future = executor.submit(APP.run)

    process = subprocess.Popen(["python3", application.__file__])
    sleep(5)
    yield "setup complete"

    # future.cancel()
    process.terminate()
    print("tear down complete")

def test_notification(soap_service):
    print("start")
    assert 2==3
    print("fin")