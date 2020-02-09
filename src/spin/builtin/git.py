from spin import api


def init(cfg):
    modified = []
    cpi = api.sh(
        "git", "status", "--porcelain=v1", capture_output=True, silent=True
    )
    for line in cpi.stdout.decode().splitlines():
        x, y = line[0], line[1]
        names = line[3:].split(" -> ")
        fname = names[-1]
        if x in "M?" or y in "M?":
            modified.append(fname)
    cfg.vcs = api.config(modified=modified)
    cpi = api.sh("git", "diff", capture_output=True, silent=True)
    cfg.vcs.unidiff = cpi.stdout
