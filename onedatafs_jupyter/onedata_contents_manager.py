# coding: utf-8
"""OnedataFS Jupyter ContentsManager implementation."""

import datetime
import errno
import mimetypes
import os
import time
import uuid

import nbformat

from notebook.services.contents.checkpoints import Checkpoints, \
        GenericCheckpointsMixin
from notebook.services.contents.manager import ContentsManager

import six

from tornado import web

from traitlets import Any, Bool, Instance, Unicode, default

from fs.onedatafs import OnedataFS, OnedataSubFS  # noqa
from fs.path import abspath, basename, dirname, join, splitext

if six.PY3:
    from base64 import encodebytes, decodebytes  # noqa
else:
    from base64 import encodestring as encodebytes, decodestring as decodebytes


class OnedataFSFileCheckpoints(GenericCheckpointsMixin, Checkpoints):
    """
    Implements the Jupyter Notebook checkpoints interface.

    Enables storing the temporary checkpoints for saved files in
    a hidden directory in a users spaces.
    """

    checkpoint_dir = Unicode(
        ".ipynb_checkpoints",
        config=True,
        help="""The directory name in which to keep file checkpoints
            This is a path relative to the file"s own directory.
            By default, it is .ipynb_checkpoints
            """,
    )
    checkpoint_bucket = Unicode(
        "", config=True, help="The bucket name where to keep file checkpoints."
                              " If empty, the current bucket is used."
    )

    def create_file_checkpoint(self, content, format, path):
        """
        Create a checkpoint of the current state of a file.

        Returns a checkpoint model for the new checkpoint.
        """
        if not self.parent.odfs.exists(self._get_checkpoint_dir(path)):
            self.parent.odfs.makedir(self._get_checkpoint_dir(path))

        checkpoint_id = str(uuid.uuid4())
        cp = self._get_checkpoint_path(checkpoint_id, path)
        self.log.debug("Creating file checkpoint %s for %s as %s",
                       checkpoint_id, path, cp)
        self.parent._save_file(cp, content, format)
        return {
            "id": checkpoint_id,
            "last_modified":
                self.parent.odfs.getinfo(cp, namespaces=['details']).modified,
        }

    def create_notebook_checkpoint(self, nb, path):
        """
        Create a checkpoint of the current state of a file.

        Returns a checkpoint model for the new checkpoint.
        """
        if not self.parent.odfs.exists(self._get_checkpoint_dir(path)):
            self.parent.odfs.makedir(self._get_checkpoint_dir(path))

        checkpoint_id = str(uuid.uuid4())
        cp = self._get_checkpoint_path(checkpoint_id, path)
        self.log.debug("Creating notebook checkpoint %s for %s as %s",
                       checkpoint_id, path, cp)
        self.parent._save_notebook(cp, nb)
        return {
            "id": checkpoint_id,
            "last_modified":
                self.parent.odfs.getinfo(cp, namespaces=['details']).modified,
        }

    def get_file_checkpoint(self, checkpoint_id, path):
        """
        Get the content of a checkpoint for a non-notebook file.

        Returns a dict of the form:
         {
             "type": "file",
             "content": <str>,
             "format": {"text","base64"},
         }
        """
        self.log.info("Restoring file %s from checkpoint %s",
                      path, checkpoint_id)
        cp = self._get_checkpoint_path(checkpoint_id, path)
        if not self.parent.odfs.file_exists(cp):
            raise web.HTTPError(404, u"No such file checkpoint: %s for %s" % (
                checkpoint_id, path))
        content, format = self.parent._read_file(cp, None)
        return {
            "type": "file",
            "content": content,
            "format": format
        }

    def get_notebook_checkpoint(self, checkpoint_id, path):
        """
        Get the content of a checkpoint for a notebook.

        Returns a dict of the form:
        {
            "type": "notebook",
            "content": <output of nbformat.read>,
        }
        """
        self.log.info("Restoring notebook %s from checkpoint %s",
                      path, checkpoint_id)
        cp = self._get_checkpoint_path(checkpoint_id, path)
        if not self.parent.odfs.exists(cp):
            raise web.HTTPError(
                404, u"No such notebook checkpoint: %s for %s" % (
                    checkpoint_id, path))
        nb = self.parent._read_notebook(cp)
        return {
            "type": "notebook",
            "content": nb
        }

    def rename_checkpoint(self, checkpoint_id, old_path, new_path):
        """Rename a single checkpoint from old_path to new_path."""
        self.log.info("Renaming checkpoint %s from %s to %s" % (
            checkpoint_id, old_path, new_path))
        old_cp = self._get_checkpoint_path(checkpoint_id, old_path)
        new_cp = self._get_checkpoint_path(checkpoint_id, new_path)
        self.parent.rename_file(old_cp, new_cp)

    def delete_checkpoint(self, checkpoint_id, path):
        """Delete a checkpoint for a file."""
        cp = self._get_checkpoint_path(checkpoint_id, path)
        self.log.info("Deleting checkpoint %s from %s" % (checkpoint_id, cp))
        self.parent.delete_file(cp)

    def list_checkpoints(self, path):
        """Return a list of checkpoints for a given file."""
        self.log.info("Listing checkpoints at %s" % (path))

        checkpoints = []

        checkpoint_dir = self._get_checkpoint_dir(path)
        if not self.parent.odfs.exists(checkpoint_dir):
            return checkpoints

        checkpoint_dirents = self.parent.odfs.listdir(checkpoint_dir)
        for file in checkpoint_dirents:
            file_name, checkpoint_id = splitext(file)

            # Consider only checkpoints for the current file
            if not file.startswith(file_name):
                continue

            # At this point checkpoint_id contains the preceding '.'
            # while length of uuid4 is 36 characters
            if len(str(checkpoint_id)) != 37:
                self.log.warning("Invalid checkpoint extension: %s" % (file))
                continue

            checkpoint_id = checkpoint_id[1:]

            info = self.parent.odfs.getinfo(join(checkpoint_dir, file),
                                            namespaces=['details'])
            checkpoints.append({
                "id": str(checkpoint_id),
                "last_modified": info.modified
                })

        checkpoints.sort(key=lambda c: c["last_modified"], reverse=False)
        self.log.debug("list_checkpoints: %s: %s", path, checkpoints)
        return checkpoints

    def _get_checkpoint_path(self, checkpoint_id, path):
        file_name = basename(path)
        dir_path = self._get_checkpoint_dir(path)
        return join(dir_path, file_name+"."+checkpoint_id)

    def _get_checkpoint_dir(self, path):
        return join(dirname(path), self.checkpoint_dir)


class OnedataFSContentsManager(ContentsManager):
    """This is an implementation of the Jupyter ContentsManager API."""

    oneprovider_host = Unicode(
        allow_none=False,
        config=True,
        help='A Oneprovider host.'
    )

    access_token = Unicode(
        allow_none=False,
        config=True,
        help='A Onedata access token.'
    )

    space = Unicode(
        allow_none=False,
        config=True,
        help='A Onedata space where the notebook will be created.'
    )

    path = Unicode(
        allow_none=True,
        config=True,
        help="""A relative path within the Onedata space which will
                be the root for the notebook.""",
        default_value=''
    )

    insecure = Bool(
        allow_none=True,
        config=True,
        help='Allow connection to Oneproviders without valid certificate',
        default_value=False
    )

    no_buffer = Bool(
        allow_none=True,
        config=True,
        help='Disable internal OnedataFS buffering.',
        default_value=False
    )

    force_proxy_io = Bool(
        allow_none=True,
        config=True,
        help='Force all data transfers to be made via Oneprovider.',
        default_value=False
    )

    force_direct_io = Bool(
        allow_none=True,
        config=True,
        help='Force all data transfer to be made directly to target storage.',
        default_value=False
    )

    post_save_hook = Any(None, config=True, allow_none=True,
                         help="""Python callable to be called on the path
                                 of a file just saved.""")

    odfs = Instance(OnedataSubFS)

    @default('odfs')
    def _odfs(self):
        abs_path = join(abspath(self.space), self.path)
        return OnedataFS(self.oneprovider_host.encode('ascii', 'replace'),
                         self.access_token.encode('ascii', 'replace'),
                         no_buffer=self.no_buffer,
                         force_proxy_io=self.force_proxy_io,
                         insecure=self.insecure).opendir(abs_path)

    @default('checkpoints_class')
    def _checkpoints_class_default(self):
        return OnedataFSFileCheckpoints

    def dir_exists(self, path):
        """
        Check if directory exists.

        Parameters
        ----------
        path : string
            The path to check
        Returns
        -------
        exists : bool
            Whether the path does indeed exist.

        """
        if not self.odfs.exists(path):
            return False

        if not self.odfs.isdir(path):
            return False

        return True

    def is_hidden(self, path):
        """
        Check if file is hidden.

        Parameters
        ----------
        path : string
            The path to check. This is an API path (`/` separated,
            relative to root dir).
        Returns
        -------
        hidden : bool
            Whether the path is hidden.

        """
        name = os.path.basename(os.path.abspath(path))
        return name.startswith('.')

    def file_exists(self, path=''):
        """
        Check if regular file exists.

        Parameters
        ----------
        path : string
            The API path of a file to check for.
        Returns
        -------
        exists : bool
            Whether the file exists.

        """
        if not self.odfs.exists(path):
            return False

        if not self.odfs.isfile(path):
            return False

        return True

    def delete_file(self, path, allow_non_empty=False):
        """Delete the file or directory at path."""
        if self.odfs.isdir(path):
            self.odfs.removetree(path)
        else:
            self.odfs.remove(path)

    def rename_file(self, old_path, new_path):
        """
        Rename a file or directory.

        N.B. Note currently we only support renaming, not moving to another
        folder. It's not clear that this operation can be performed using
        rename, it doesn't seem to be exposed through jlab.
        """
        self.odfs.move(old_path, new_path)

    def _base_model(self, path):
        """Build the common base of a contents model."""
        try:
            info = self.odfs.getinfo(path, namespaces=['details'])
            size = info.size
            last_modified = info.modified
            created = info.created
        except Exception:
            self.log.warning("Cannot get info of file: %s" % (path))
            size = None
            created = datetime.datetime.now()
            last_modified = created

        model = {}
        model['name'] = basename(path)
        model['path'] = path
        model['last_modified'] = last_modified
        model['created'] = created
        model['content'] = None
        model['format'] = None
        model['mimetype'] = None
        model['size'] = size

        try:
            model['writable'] = True  # TODO
        except OSError:
            self.log.error("Failed to check write permissions on %s", path)
            model['writable'] = False

        self.log.info("Base notebook model last modified date: %s",
                      str(last_modified))
        self.log.info("Base notebook model now date: %s",
                      str(datetime.datetime.now()))

        self.log.info("Created base notebook model: %s", str(model))

        return model

    def _dir_model(self, path, content=True):
        """
        Build a model for a directory.

        If content is requested, will include a listing of the directory
        """
        if not self.odfs.isdir(path):
            raise web.HTTPError(404, u'directory does not exist: %r' % path)

        model = self._base_model(path)
        model['type'] = 'directory'
        model['size'] = None
        if content:
            model['content'] = contents = []
            for name in self.odfs.listdir(path):
                try:
                    entry_path = join(path, name)
                except UnicodeDecodeError as e:
                    self.log.warning(
                        "failed to decode filename '%s': %s", name, e)
                    continue

                try:
                    self.odfs.getinfo(entry_path)
                except OSError as e:
                    # skip over broken symlinks in listing
                    if e.errno == errno.ENOENT:
                        self.log.warning("%s doesn't exist", entry_path)
                    else:
                        self.log.warning("Error stat-ing %s: %s",
                                         entry_path, e)
                    continue

                contents.append(self.get(path='%s/%s' %
                                         (path, name), content=False))

            model['format'] = 'json'

        return model

    def _file_model(self, path, content=True, format=None):
        """
        Build a model for a file.

        If content is requested, include the file contents.
        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64
        """
        model = self._base_model(path)
        model['type'] = 'file'

        model['mimetype'] = mimetypes.guess_type(path)[0]

        if content:
            content, format = self._read_file(path, format)
            if model['mimetype'] is None:
                default_mime = {
                    'text': 'text/plain',
                    'base64': 'application/octet-stream'
                }[format]
                model['mimetype'] = default_mime

            model.update(
                content=content,
                format=format,
            )

        return model

    def _notebook_model(self, path, content=True):
        """
        Build a notebook model.

        If content is requested, the notebook content will be populated
        as a JSON structure (not double-serialized)
        """
        model = self._base_model(path)
        model['type'] = 'notebook'

        if content:
            nb = self._read_notebook(path, as_version=4)
            self.mark_trusted_cells(nb, path)
            model['content'] = nb
            model['format'] = 'json'
            self.validate_notebook_model(model)

        return model

    def get(self, path, content=True, type=None, format=None):
        """
        Take a path for an entity and returns its model.

        Parameters
        ----------
        path : str
            the API path that describes the relative path for the target
        content : bool
            Whether to include the contents in the reply
        type : str, optional
            The requested type - 'file', 'notebook', or 'directory'.
            Will raise HTTPError 400 if the content doesn't match.
        format : str, optional
            The requested format for file contents. 'text' or 'base64'.
            Ignored if this returns a notebook or directory model.
        Returns
        -------
        model : dict
            the contents model. If content=True, returns the contents
            of the file or directory as well.

        """
        if not self.exists(path):
            raise web.HTTPError(404, u'No such file or directory: %s' % path)

        if self.odfs.isdir(path):
            if type not in (None, 'directory'):
                raise web.HTTPError(
                        400, u'%s is a directory, not a %s' % (path, type),
                        reason='bad type')
            model = self._dir_model(path, content=content)
        elif type == 'notebook' or (type is None and path.endswith('.ipynb')):
            self.log.debug("Getting notebook from file %s" % (path))
            model = self._notebook_model(path, content=content)
        else:
            if type == 'directory':
                raise web.HTTPError(
                        400, u'%s is not a directory' % path,
                        reason='bad type')
            model = self._file_model(path, content=content, format=format)
        return model

    def _save_directory(self, path, model, spath=''):
        """Create a directory."""
        if not self.odfs.exists(path):
            self.odfs.makedir(path)
        elif not self.odfs.isdir(path):
            raise web.HTTPError(400, u'Not a directory: %s' % (path))
        else:
            self.log.debug("Directory %r already exists", path)

    def save(self, model, path=''):
        """Save the file model and return the model with no content."""
        if 'type' not in model:
            raise web.HTTPError(400, u'No file type provided')
        if 'content' not in model and model['type'] != 'directory':
            raise web.HTTPError(400, u'No file content provided')

        self.log.info("Saving file model %s (ts=%s)", path, time.time())

        self.run_pre_save_hook(model=model, path=path)

        try:
            if model['type'] == 'notebook':
                notebook = nbformat.from_dict(model['content'])
                self.check_and_sign(notebook, path)
                self._save_notebook(path, notebook)
            elif model['type'] == 'file':
                self._save_file(path, model['content'], model.get('format'))
            elif model['type'] == 'directory':
                self._save_directory(path, model, path)
            else:
                raise web.HTTPError(
                        400, "Unhandled contents type: %s" % model['type'])
        except web.HTTPError:
            raise
        except Exception as e:
            self.log.error(u'Error while saving file: %s %s', path, e,
                           exc_info=True)
            raise web.HTTPError(
                    500,
                    u'Unexpected error while saving file: %s %s' % (path, e))

        validation_message = None
        if model['type'] == 'notebook':
            self.validate_notebook_model(model)
            validation_message = model.get('message', None)
            self.log.warning("Model validation message: %s", validation_message)

        model = self.get(path, content=False)
        if validation_message:
            model['message'] = validation_message

        self.run_post_save_hook(model=model, os_path=path)

        # Update the creation date in the notebook model, in case the
        # Oneprovider has a time shift of few seconds with respect to th
        # client machine
        model['last_modified'] = self.odfs.getinfo(
                path, namespaces=['details']).modified

        return model

    def _save_file(self, path, content, format):
        """Save content of a generic file."""
        if format not in {'text', 'base64'}:
            raise web.HTTPError(
                400,
                "Must specify format of file contents as 'text' or 'base64'",
            )
        try:
            if format == 'text':
                bcontent = content.encode('utf8')
            else:
                b64_bytes = content.encode('ascii')
                bcontent = decodebytes(b64_bytes)
        except Exception as e:
            raise web.HTTPError(
                400, u'Encoding error saving %s: %s' % (path, e)
            )

        if not self.odfs.exists(path):
            self.odfs.create(path)

        with self.odfs.openbin(path, 'rw+') as f:
            f.write(bcontent)

    def _read_notebook(self, path, as_version=4):
        """Read a notebook from an os path."""
        try:
            nb_bytes = self.odfs.readbytes(path)
            notebook = nbformat.reads(nb_bytes.decode('utf8'),
                                      as_version=as_version)
            self.log.warning("Decoded notebook from file: %s", notebook)
            return notebook
        except Exception as e:
            self.log.error("Cannot read notebook %s",
                           str(nb_bytes.decode('utf8')))
            raise e

    def _save_notebook(self, path, nb):
        """Save a notebook to a path."""
        self.log.warning("Saving notebook model %s (ts=%s)", path, time.time())

        try:
            nb_string = nbformat.writes(
                    nb, version=nbformat.NO_CONVERT).encode('utf8')

            if six.PY2:
                nb_bytes = bytes(nb_string)
            else:
                nb_bytes = nb_string

            self.odfs.create(path, wipe=True)

            truncated_size = len(self.odfs.readbytes(path))
            if truncated_size > 0:
                self.log.error("File %s not empty after truncate: %d!!!",
                               path, truncated_size)

            self.odfs.writebytes(path, nb_bytes)

            # Update the notebook mtime to subsecond accuracy
            # to avoid the warning about the notebook being changed on disk
            self.odfs.setinfo(path, {'details': {'modified': time.time()}})

            self.log.debug("Notebook saved at: %s" % (
                str(datetime.datetime.now())))
            self.log.debug("Notebook file modified date: %s" % (
                str(self.odfs.getinfo(path, namespaces=['details']).modified)))
        except ValueError as error:
            self.log.error("Tried to save invalid JSON to model: %s",
                           nb_string.decode('utf8'))
            raise error
        except TypeError as error:
            self.log.error("Failed encoding the model: %s",
                           str(nb_string))
            raise error

    def _read_file(self, path, format):
        """
        Read a non-notebook file.

        path: The path to be read.
        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64

        """
        if not self.odfs.isfile(path):
            raise web.HTTPError(400, "Cannot read non-file %s" % path)

        with self.odfs.openbin(path, 'r') as f:
            bcontent = f.read()

        if format is None or format == 'text':
            # Try to interpret as unicode if format is unknown or if unicode
            # was explicitly requested.
            try:
                return bcontent.decode('utf8'), 'text'
            except UnicodeError:
                if format == 'text':
                    raise web.HTTPError(
                        400,
                        "%s is not UTF-8 encoded" % path,
                        reason='bad format',
                    )
        return encodebytes(bcontent).decode('ascii'), 'base64'

    def run_post_save_hook(self, model, os_path):
        """Run the post-save hook if defined, and log errors."""
        if self.post_save_hook:
            try:
                self.log.debug("Running post-save hook on %s", os_path)
                self.post_save_hook(
                    os_path=os_path, model=model, contents_manager=self)
            except Exception as e:
                self.log.error("Post-save hook failed o-n %s",
                               os_path, exc_info=True)
                raise web.HTTPError(
                    500, u'Unexpected error while running post hook save: %s'
                    % e)
