class ZypperRepo():
    def __init__(self, **kwargs):
        self.name = kwargs.get('name', '')
        self.url = kwargs.get('url', '')
        self.priority = kwargs.get('priority', None)
