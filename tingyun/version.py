

def get_version(version):
    """Returns a PEP 386-compliant version number from VERSION.

    """
    version_mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
    assert len(version) == 5
    assert version[3] in ('alpha', 'beta', 'rc', 'final')

    parts = 3
    main = '.'.join(str(x) for x in version[:parts])
    sub = ''
    if version[3] != 'final':
        sub = version_mapping[version[3]] + str(version[4])

    return str(main + sub)