# OnedataFS Jupyter Content Manager

This is an implementation of the Jupyter Content Manager API, allowing to run
Jupyter Notebooks directly on top of Onedata spaces.

OnedataFS is a [PyFilesystem](https://www.pyfilesystem.org/) interface to
[Onedata](https://onedata.org) virtual file system.


## Installing

You can install OnedataFS Jupyter Contents Manager using our packages:

```
wget https://get.onedata.org/oneclient.sh

# For Python2
sh oneclient.sh python-onedatafs-jupyter

# For Python3
sh oneclient.sh python3-onedatafs-jupyter
```

## Configuring Jupyter

In order to configure Jupyter Notebook to work directly in a Onedata Space,
add the following lines to the Jupyter configuration file:

```python
import sys

c = get_config()

c.NotebookApp.contents_manager_class = 'onedatafs_jupyter.OnedataFSContentsManager'

# Hostname or IP of the Oneprovider to which the Jupyter should connect
c.OnedataFSContentsManager.oneprovider_host = u'datahub.egi.eu'

# The Onedata user access token
c.OnedataFSContentsManager.access_token = u'MDAzN2xvY2F00aW...'

# Name of the space, where the notebooks should be stored
c.OnedataFSContentsManager.space = u'/experiment-1'

# Internal path within a data space, for instance to a subdirectory where Jupyter 
# notebooks should be stored, must be relative (i.e. cannot start with `/`)
c.OnedataFSContentsManager.path = u''

# When True, allow connection to Oneprovider instances without trusted certificates
c.OnedataFSContentsManager.insecure = True

# When True, disables internal OnedataFS buffering, should be set to False for
# use cases handling larger files
c.OnedataFSContentsManager.no_buffer = True

# With these settings, all data transfers between Jupyter and Onedata will be performed
# in ProxyIO mode, without direct access to the backend storage. For testing
# and use cases with small files this is ok, but for high-performance calculation
# the following 2 lines should be negated
c.OnedataFSContentsManager.force_proxy_io = True
c.OnedataFSContentsManager.force_direct_io = False

# Set the log level
c.Application.log_level = 'DEBUG'

# The following line disables Jupyter authentication, for production deployments
# remove it or provide a custom token
c.NotebookApp.token = ''
```

When starting Jupyter using a Docker (assuming the container contains all necessary dependencies),
the configuration file can be easily mapped to the Jupyter using volume option, e.g.:

```
docker run -v $PWD/my_jupyter_notebook_config.py:/root/.jupyter/jupyter_notebook_config.py -it onedata/onedatafs-jupyter
```

If you don't have a config yet, create it using:

```bash
jupyter notebook --generate-config
```

## Documentation

- [PyFilesystem Wiki](https://www.pyfilesystem.org)
- [OnedataFS Reference](http://fs-onedatafs.readthedocs.io/en/latest/)
- [Onedata Homepage](https://onedata.org)
