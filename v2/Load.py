class Load:
    """
    FALTA DOCUMENTAR XDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD
    """
    def __init__(self, file, offset, bytesToHandle):
        self._file = file
        self._offset = offset
        self._bytesToHandle = bytesToHandle
        self._end = offset + bytesToHandle

    def getFile(self):
        return self._file

    def getOffset(self):
        return self._offset
    
    def getBytesToHandle(self):
        return self._bytesToHandle

    def getEnd(self):
        return self._end