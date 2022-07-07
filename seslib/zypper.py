class ZypperRepo():
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        self.url = kwargs.get('url', '')
        self.priority = kwargs.get('priority', None)


class ZypperPackage():
    def __init__(self, **kwargs):
        self.state = kwargs.get('state', '')
        self.repo = kwargs.get('repo', '')
        self.name = kwargs.get('name', '')
        self.version = kwargs.get('version', '')
        self.arch = kwargs.get('arch', '')
