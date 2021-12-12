#!/usr/bin/python3

import sys
import errno
import stat
import time
import ctypes

from fusepy import FUSE, FuseOSError, Operations

from amitools.fs.ADFSVolume import ADFSVolume
from amitools.fs.ADFSDir import ADFSDir
from amitools.fs.ADFSFile import ADFSFile
from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
from amitools.fs.FSString import FSString


class XDF(Operations):

    def __init__(self, filename):
        f = BlkDevFactory()
        self.blkdev = f.open(filename, read_only=True)
        self.vol = ADFSVolume(self.blkdev)
        self.vol.open()
        self.mounted = time.time()

    def destroy(self, path):
        self.vol.close()
        self.blkdev.close()
    
    def getattr(self, path, fh=None):
        # TODO: actual times and flags
        attrs = dict(
            st_ctime=self.mounted,
            st_mtime=self.mounted,
            st_atime=self.mounted,
            st_nlink=2
        )
        dir_mode = stat.S_IFDIR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP  # r-xr-x---
        file_mode = stat.S_IFREG | stat.S_IRUSR | stat.S_IRGRP  # r--r-----
        
        if path == '/':
            attrs.update(dict(st_mode=dir_mode))
            return attrs
        
        node = self.get_node_by_path(path)
        if node == None:
            raise FuseOSError(errno .ENOENT)
        
        if isinstance(node, ADFSFile):
            attrs.update(dict(st_mode=(file_mode), st_size=node.block.byte_size))
        elif isinstance(node, ADFSDir):
            attrs.update(dict(st_mode=(dir_mode)))

        return attrs

    def read(self, path, size, offset, fh):
        node = self.get_node_by_path(path)
        content = node.get_file_data()[offset : offset + size]
        char_array = ctypes.c_char * len(content)
        
        return char_array.from_buffer(content)

    def readdir(self, path, fh):
        if path == '/':
            directory = self.vol.root_dir
        else:
            directory = self.get_node_by_path(path)
        entries = directory.get_entries_sorted_by_name()
        
        return ['.', '..'] + list(map(lambda entry: entry.name.get_unicode_name(), entries))
    
    def get_node_by_path(self, path):
        levels = path.split('/')[1:]
        ami_path = '/'.join(levels)  # TODO: path delimiter
        
        return self.vol.get_path_name(FSString(ami_path))


def main():
    if len(sys.argv) != 3:
        print('Usage: %s <image> <mountpoint>' % sys.argv[0])
        exit(1)

    FUSE(XDF(sys.argv[1]), sys.argv[2], foreground=True, nothreads=True, allow_other=False)


if __name__ == '__main__':
    main()
