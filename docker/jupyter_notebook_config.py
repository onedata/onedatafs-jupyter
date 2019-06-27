#
# This file contains a template for configuring Jupyter server
# to use Onedata as the Contents Manager.
#
import sys

c = get_config()

c.NotebookApp.contents_manager_class = 'onedatafs_jupyter.OnedataFSContentsManager'

#
# Set the following variables
#
c.OnedataFSContentsManager.oneprovider_host = u''
c.OnedataFSContentsManager.access_token = u''
c.OnedataFSContentsManager.space = u'/space1'
c.OnedataFSContentsManager.path = u''
c.OnedataFSContentsManager.insecure = True
c.OnedataFSContentsManager.no_buffer = True
c.OnedataFSContentsManager.force_proxy_io = True

c.Application.log_level = 'DEBUG'

#
# Comment to enable actual token
#
c.NotebookApp.token = ''
