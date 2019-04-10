# OnedataFS

OnedataFS is a [PyFilesystem](https://www.pyfilesystem.org/) interface to
[Onedata](https://onedata.org) virtual file system.

As a PyFilesystem concrete class, [OnedataFS](https://github.com/onedata/fs-onedatafs/) allows you to work with Onedata in the same way as any other supported filesystem.

## Installing

You can install OnedataFS Jupyter Contents Manager from pip as follows:

```
pip install onedatafs-jupyter
```

## Opening a OnedataFS

Open an OnedataFS by explicitly using the constructor:

```python
from fs_onedatafs import OnedataFS
onedata_provider_host = "..."
onedata_access_token = "..."
odfs = OnedataFS(onedata_provider_host, onedata_access_token)
```

Or with a FS URL:

```python
  from fs import open_fs
  odfs = open_fs('onedatafs://HOST?token=...')
```

## Extended attributes

Onedata FS supports in addition to standard PyFilesystem API operations
on metadata via POSIX compatible extended attributes API.


## Documentation

- [PyFilesystem Wiki](https://www.pyfilesystem.org)
- [OnedataFS Reference](http://fs-onedatafs.readthedocs.io/en/latest/)
- [Onedata Homepage](https://onedata.org)
