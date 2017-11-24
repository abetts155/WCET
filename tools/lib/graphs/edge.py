class Edge:
    def __init__(self, predecessor, successor):
        self._predecessor = predecessor
        self._successor = successor

    def predecessor(self):
        return self._predecessor

    def successor(self):
        return self._successor

    def __str__(self):
        return "({},{})".format(self._predecessor.id, self._successor.id)


class PathEdge(Edge):
    def __init__(self, predecessor, successor):
        Edge.__init__(self, predecessor, successor)
        self._path = []

    def extend(self, path):
        self._path.extend(path)

    @property
    def path(self):
        return self._path


class CallGraphEdge(Edge):
    def __init__(self, predecessor, successor, call_sites):
        Edge.__init__(self, predecessor, successor)
        self._call_sites = call_sites

    @property
    def call_sites(self):
        return self._call_sites