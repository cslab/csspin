from spin import task
import webbrowser


@task()
def cedm(cfg):
    webbrowser.open("https://cedm.contact.de")

def xyz():
    pass
