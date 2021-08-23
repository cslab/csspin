"""
Helper file to find the abi tag of the target interpreter of the venv.
"""


def get_abi_tag():
    try:
        from packaging import tags

        # tag for running interpreter (most important priority)
        tag = next(tags.sys_tags())
        print(tag.abi)
    except ImportError:
        from pip._internal.pep425tags import get_abi_tag

        print(get_abi_tag())


if __name__ == "__main__":
    get_abi_tag()
