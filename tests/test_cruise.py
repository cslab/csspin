from spin import cli, cruise


def test_cruise():
    cfg = cli.load_spinfile("spinfile.yaml")

    def match(*selectors):
        return [name for name, _ in cruise.match_cruises(cfg, *selectors)]

    assert "cp27-win" in match("cp27-win")
    assert "host" in match("@all")
    assert "host" not in match("@docker")
