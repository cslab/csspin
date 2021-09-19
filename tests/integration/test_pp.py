from spin import backtick, sh


def test_python():
    sh("spin -C tests/integration -f python.yaml --provision")
    sh("spin -C tests/integration -f python.yaml run which python")
    assert (
        backtick("spin -q -C tests/integration -f python.yaml python --version")
        == "Python 3.9.6\n"
    )
