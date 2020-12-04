class Match:
    """
    TODO: Comentar
    """
    def __init__(self, file, lineNumber, lineContent, amount):
        self._lineNumber = lineNumber
        self._lineContent = lineContent
        self._file = file
        self._amount = amount

    def getLineNumber(self):
        return self._lineNumber

    def getLineContent(self):
        return self._lineContent
    
    def getFile(self):
        return self._file

    def getAmount(self):
        return self._amount