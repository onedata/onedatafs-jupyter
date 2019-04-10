# OnedataFS Jupyter Content Manager

This is an implementation of the Jupyter Content Manager API, allowing to run
Jupyter Notebooks directly on top of Onedata spaces.

OnedataFS is a [PyFilesystem](https://www.pyfilesystem.org/) interface to
[Onedata](https://onedata.org) virtual file system.


## Installing

You can install OnedataFS Jupyter Contents Manager from pip as follows:

```
pip install onedatafs-jupyter
```

## Configuring Jupyter

In order to configure Jupyter Notebook to work directly in a Onedata Space,
add the following lines to the Jupyter configuration file:

```python
import sys
sys.path.append('/opt/oneclient/lib')

c = get_config()

c.NotebookApp.contents_manager_class = 'onedatafs_jupyter.onedata_contents_manager.OnedataFSContentsManager'
c.OnedataFSContentsManager.oneprovider_host = u'oneprovider.example.com'
c.OnedataFSContentsManager.access_token = u'MDAxN...'
```

If you don't have a config yet, create it using:

```bash
jupyter notebook --generate-config
```

## Documentation

- [PyFilesystem Wiki](https://www.pyfilesystem.org)
- [OnedataFS Reference](http://fs-onedatafs.readthedocs.io/en/latest/)
- [Onedata Homepage](https://onedata.org)
