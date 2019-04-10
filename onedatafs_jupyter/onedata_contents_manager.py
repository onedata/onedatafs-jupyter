import os
from six import BytesIO
import base64
import nbformat

from notebook.services.contents.manager import ContentsManager
from notebook.services.contents.filecheckpoints import GenericFileCheckpoints

from traitlets import default, Unicode, Instance, Any

from tornado import web

from fs_onedatafs import OnedataFS, OnedataSubFS

from fs.path import abspath, join

try: #PY3
    from base64 import encodebytes, decodebytes
except ImportError: #PY2
    from base64 import encodestring as encodebytes, decodestring as decodebytes


class OnedataFSContentsManager(ContentsManager):

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
        help='A relative path within the Onedata space which will be the root for the notebook.',
        default_value=''
    )

    post_save_hook = Any(None, config=True, allow_none=True,
        help="""Python callable or importstring thereof
        to be called on the path of a file just saved.
        This can be used to process the file on disk,
        such as converting the notebook to a script or HTML via nbconvert.
        It will be called as (all arguments passed by keyword)::
            hook(os_path=os_path, model=model, contents_manager=instance)
        - path: the filesystem path to the file just written
        - model: the model representing the file
        - contents_manager: this ContentsManager instance
        """
    )

    odfs = Instance(OnedataSubFS)

    @default('odfs')
    def _odfs(self):
    	print("Opening directory: " + join(abspath(self.space), self.path))
        return OnedataFS(self.oneprovider_host.encode('ascii', 'replace'), self.access_token.encode('ascii', 'replace'), force_proxy_io=True, insecure=True).opendir(join(abspath(self.space), self.path))

    @default('checkpoints_class')
    def _checkpoints_class(self):
        return GenericFileCheckpoints

    @default('checkpoints_kwargs')
    def _checkpoints_kwargs(self):
        return {
            'root_dir': u'/.ipynb_checkpoints'
        }

    def dir_exists(self, path):
        """Does a directory exist at the given path?
        Like os.path.isdir

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
        """Is path a hidden directory or file?
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

        return False

    def file_exists(self, path=''):
        """Does a file exist at the given path?
        Like os.path.isfile

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
        self.odfs.remove(path)

    def rename_file(self, old_path, new_path):
        """
        Rename a file or directory.

        N.B. Note currently we only support renaming, not moving to another folder.
        Its not clear that this operation can be performed using rename, it doesn't
        seem to be exposed through jlab.
        """
        self.odfs.move(old_path, new_path)

    def _base_model(self, path):
        """Build the common base of a contents model"""
        info = self.odfs.getinfo(path, namespaces=['details'])

        try:
            # size of file
            size = info.size
        except (ValueError, OSError):
            self.log.warning('Unable to get size.')
            size = None

        try:
            last_modified = info.modified
        except (ValueError, OSError):
            # Files can rarely have an invalid timestamp
            # https://github.com/jupyter/notebook/issues/2539
            # https://github.com/jupyter/notebook/issues/2757
            # Use the Unix epoch as a fallback so we don't crash.
            self.log.warning('Invalid mtime %s for %s', str(info.modified), path)
            last_modified = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

        try:
            created = info.created
        except (ValueError, OSError):  # See above
            self.log.warning('Invalid ctime %s for %s', str(info.created), path)
            created = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

        # Create the base model.
        model = {}
        model['name'] = path.rsplit('/', 1)[-1]
        model['path'] = path
        model['last_modified'] = last_modified
        model['created'] = created
        model['content'] = None
        model['format'] = None
        model['mimetype'] = None
        model['size'] = size

        try:
            model['writable'] = True # TODO
        except OSError:
            self.log.error("Failed to check write permissions on %s", path)
            model['writable'] = False
        return model

    def _dir_model(self, path, content=True):
        """Build a model for a directory
        if content is requested, will include a listing of the directory
        """
        four_o_four = u'directory does not exist: %r' % path

        if not self.odfs.isdir(path):
            raise web.HTTPError(404, four_o_four)
        # elif is_hidden(path, self.root_dir) and not self.allow_hidden:
            # self.log.info("Refusing to serve hidden directory %r, via 404 Error",
                # path
            # )
            # raise web.HTTPError(404, four_o_four)

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
                    attr = self.odfs.getinfo(entry_path)
                except OSError as e:
                    # skip over broken symlinks in listing
                    if e.errno == errno.ENOENT:
                        self.log.warning("%s doesn't exist", entry_path)
                    else:
                        self.log.warning("Error stat-ing %s: %s", entry_path, e)
                    continue

		#if self.should_list(name):
		    # if self.allow_hidden or not is_file_hidden(path, stat_res=st):
		contents.append(self.get(path='%s/%s' % (path, name), content=False))

            model['format'] = 'json'

        return model


    def _file_model(self, path, content=True, format=None):
        """Build a model for a file
        if content is requested, include the file contents.
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
        """Build a notebook model
        if content is requested, the notebook content will be populated
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
        """ Takes a path for an entity and returns its model
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
                raise web.HTTPError(400,
                                u'%s is a directory, not a %s' % (path, type), reason='bad type')
            model = self._dir_model(path, content=content)
        elif type == 'notebook' or (type is None and path.endswith('.ipynb')):
            model = self._notebook_model(path, content=content)
        else:
            if type == 'directory':
                raise web.HTTPError(400,
                                u'%s is not a directory' % path, reason='bad type')
            model = self._file_model(path, content=content, format=format)
        return model

    def _save_directory(self, path, model, spath=''):
        """create a directory"""
        if is_hidden(path, self.root_dir) and not self.allow_hidden:
            raise web.HTTPError(400, u'Cannot create hidden directory %r' % path)
        if not self.odfs.exists(path):
            with self.perm_to_403():
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

        self.log.debug("Saving %s", path)

        self.run_pre_save_hook(model=model, path=path)

        try:
            if model['type'] == 'notebook':
                nb = nbformat.from_dict(model['content'])
                self.check_and_sign(nb, path)
                self._save_notebook(path, nb)
                # One checkpoint should always exist for notebooks.
                if not self.checkpoints.list_checkpoints(path):
                    self.create_checkpoint(path)
            elif model['type'] == 'file':
                # Missing format will be handled internally by _save_file.
                self._save_file(path, model['content'], model.get('format'))
            elif model['type'] == 'directory':
                self._save_directory(path, model, path)
            else:
                raise web.HTTPError(400, "Unhandled contents type: %s" % model['type'])
        except web.HTTPError:
            raise
        except Exception as e:
            self.log.error(u'Error while saving file: %s %s', path, e, exc_info=True)
            raise web.HTTPError(500, u'Unexpected error while saving file: %s %s' % (path, e))

        validation_message = None
        if model['type'] == 'notebook':
            self.validate_notebook_model(model)
            validation_message = model.get('message', None)

        model = self.get(path, content=False)
        if validation_message:
            model['message'] = validation_message

        self.run_post_save_hook(model=model, os_path=path)

        return model

    def _save_file(self, path, content, format):
        """Save content of a generic file."""
        if format not in {'text', 'base64'}:
            raise HTTPError(
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
            raise HTTPError(
                400, u'Encoding error saving %s: %s' % (os_path, e)
            )

	if not self.odfs.exists(path):
	    self.odfs.create(path)

        with self.odfs.openbin(path, 'rw+') as f:
            f.write(bcontent)

    def _read_notebook(self, path, as_version=4):
        """Read a notebook from an os path."""
        with self.odfs.openbin(path, 'r') as f:
            try:
                return nbformat.read(f, as_version=as_version)
            except Exception as e:
                e_orig = e

            # If use_atomic_writing is enabled, we'll guess that it was also
            # enabled when this notebook was written and look for a valid
            # atomic intermediate.
            tmp_path = path_to_intermediate(path)

            if not self.use_atomic_writing or not self.odfs.exists(tmp_path):
                raise HTTPError(
                    400,
                    u"Unreadable Notebook: %s %r" % (path, e_orig),
                )

            # Move the bad file aside, restore the intermediate, and try again.
            invalid_file = path_to_invalid(path)
            replace_file(path, invalid_file)
            replace_file(tmp_path, path)
            return self._read_notebook(path, as_version)

    def _save_notebook(self, path, nb):
        """Save a notebook to an path."""
	if not self.odfs.exists(path):
	    self.odfs.create(path)

        with self.odfs.openbin(path, "rw+") as f:
            nbformat.write(nb, f, version=nbformat.NO_CONVERT)

    def _read_file(self, path, format):
        """Read a non-notebook file.
        os_path: The path to be read.
        format:
          If 'text', the contents will be decoded as UTF-8.
          If 'base64', the raw bytes contents will be encoded as base64.
          If not specified, try to decode as UTF-8, and fall back to base64
        """
        if not self.odfs.isfile(path):
            raise HTTPError(400, "Cannot read non-file %s" % path)

        with self.openbin(path, 'r') as f:
            bcontent = f.read()

        if format is None or format == 'text':
            # Try to interpret as unicode if format is unknown or if unicode
            # was explicitly requested.
            try:
                return bcontent.decode('utf8'), 'text'
            except UnicodeError:
                if format == 'text':
                    raise HTTPError(
                        400,
                        "%s is not UTF-8 encoded" % path,
                        reason='bad format',
                    )
        return encodebytes(bcontent).decode('ascii'), 'base64'

    def run_post_save_hook(self, model, os_path):
        """Run the post-save hook if defined, and log errors"""
        if self.post_save_hook:
            try:
                self.log.debug("Running post-save hook on %s", os_path)
                self.post_save_hook(os_path=os_path, model=model, contents_manager=self)
            except Exception as e:
                self.log.error("Post-save hook failed o-n %s", os_path, exc_info=True)
                raise web.HTTPError(500, u'Unexpected error while running post hook save: %s' % e)

