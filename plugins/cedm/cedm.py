import webbrowser

from spin import task


@task()
def cedm(cfg):
    webbrowser.open("https://cedm.contact.de")


def xyz():
    pass
