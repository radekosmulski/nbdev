# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/11_clean.ipynb.

# %% auto 0
__all__ = ['nbdev_trust', 'clean_nb', 'process_write', 'nbdev_clean', 'clean_jupyter', 'nbdev_install_hooks']

# %% ../nbs/11_clean.ipynb 2
import ast,warnings,stat
from astunparse import unparse
from textwrap import indent

from execnb.nbio import *
from fastcore.script import *
from fastcore.basics import *
from fastcore.imports import *

from .imports import *
from .read import *
from .sync import *
from .process import first_code_ln

# %% ../nbs/11_clean.ipynb 6
@call_parse
def nbdev_trust(
    fname:str=None,  # A notebook name or glob to trust
    force_all:bool=False  # Also trust notebooks that haven't changed
):
    "Trust notebooks matching `fname`"
    try: from nbformat.sign import NotebookNotary
    except:
        import warnings
        warnings.warn("Please install jupyter and try again")
        return

    fname = Path(fname if fname else config_key("nbs_path"))
    path = fname if fname.is_dir() else fname.parent
    check_fname = path/".last_checked"
    last_checked = os.path.getmtime(check_fname) if check_fname.exists() else None
    nbs = globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]') if fname.is_dir() else [fname]
    for fn in nbs:
        if last_checked and not force_all:
            last_changed = os.path.getmtime(fn)
            if last_changed < last_checked: continue
        nb = read_nb(fn)
        if not NotebookNotary().check_signature(nb): NotebookNotary().sign(nb)
    check_fname.touch(exist_ok=True)

# %% ../nbs/11_clean.ipynb 9
def _clean_cell_output(cell):
    "Remove execution count in `cell`"
    if 'outputs' in cell:
        for o in cell['outputs']:
            if 'execution_count' in o: o['execution_count'] = None
            o.get('data',{}).pop("application/vnd.google.colaboratory.intrinsic+json", None)
            o.get('metadata', {}).pop('tags', None)

# %% ../nbs/11_clean.ipynb 10
def _clean_cell(cell, clear_all=False, allowed_metadata_keys=None):
    "Clean `cell` by removing superfluous metadata or everything except the input if `clear_all`"
    if 'execution_count' in cell: cell['execution_count'] = None
    if 'outputs' in cell:
        if clear_all: cell['outputs'] = []
        else:         _clean_cell_output(cell)
    if cell['source'] == ['']: cell['source'] = []
    cell['metadata'] = {} if clear_all else {
        k:v for k,v in cell['metadata'].items() if k in allowed_metadata_keys}

# %% ../nbs/11_clean.ipynb 11
def clean_nb(
    nb, # The notebook to clean
    clear_all=False, # Remove all cell metadata and cell outputs
    allowed_metadata_keys:list=None, # Preserve the list of keys in the main notebook metadata
    allowed_cell_metadata_keys:list=None # Preserve the list of keys in cell level metadata
):
    "Clean `nb` from superfluous metadata"
    metadata_keys = {"kernelspec", "jekyll", "jupytext", "doc"}
    if allowed_metadata_keys: metadata_keys.update(allowed_metadata_keys)
    cell_metadata_keys = {"hide_input"}
    if allowed_cell_metadata_keys: cell_metadata_keys.update(allowed_cell_metadata_keys)
    for c in nb['cells']: _clean_cell(c, clear_all=clear_all, allowed_metadata_keys=cell_metadata_keys)
    nb['metadata'] = {k:v for k,v in nb['metadata'].items() if k in metadata_keys}

# %% ../nbs/11_clean.ipynb 20
def _reconfigure(*strms):
    for s in strms:
        if hasattr(s,'reconfigure'): s.reconfigure(encoding='utf-8')

# %% ../nbs/11_clean.ipynb 22
def process_write(warn_msg, proc_nb, f_in, f_out=None, disp=False):
    if not f_out: f_out = sys.stdout if disp else f_in
    if isinstance(f_in, (str,Path)): f_in = Path(f_in).open()
    try:
        _reconfigure(f_in, f_out)
        nb = loads(f_in.read())
        proc_nb(nb)
        write_nb(nb, f_out)
    except Exception as e:
        warn(f'{warn_msg}')
        warn(e)

# %% ../nbs/11_clean.ipynb 23
def _nbdev_clean(nb, path=None, **kwargs):
    cfg = get_config(path=path)
    allowed_metadata_keys = cfg.get("allowed_metadata_keys").split()
    allowed_cell_metadata_keys = cfg.get("allowed_cell_metadata_keys").split()
    return clean_nb(nb, allowed_metadata_keys=allowed_metadata_keys,
                    allowed_cell_metadata_keys=allowed_cell_metadata_keys, **kwargs)

# %% ../nbs/11_clean.ipynb 24
@call_parse
def nbdev_clean(
    fname:str=None, # A notebook name or glob to clean
    clear_all:bool=False, # Clean all metadata and outputs
    disp:bool=False,  # Print the cleaned outputs
    stdin:bool=False # Read notebook from input stream
):
    "Clean all notebooks in `fname` to avoid merge conflicts"
    # Git hooks will pass the notebooks in stdin
    _clean = partial(_nbdev_clean, clear_all=clear_all)
    _write = partial(process_write, warn_msg='Failed to clean notebook', proc_nb=_clean)
    if stdin: return _write(f_in=sys.stdin, f_out=sys.stdout)
    
    if fname is None: fname = config_key("nbs_path")
    for f in globtastic(fname, file_glob='*.ipynb', skip_folder_re='^[_.]'): _write(f_in=f, disp=disp)

# %% ../nbs/11_clean.ipynb 27
def clean_jupyter(path, model, **kwargs):
    "Clean Jupyter `model` pre save to `path`"
    if not (model['type']=='notebook' and model['content']['nbformat']==4): return
    get_config.cache_clear() # Allow config changes without restarting Jupyter
    jupyter_hooks = get_config(path=path).jupyter_hooks
    if jupyter_hooks in {'user','nbdev','none'}:
        warn(("`jupyter_hooks` values in `{'user','nbdev','none'}` are deprecated. Use `True` or `False` instead.\n"
              "See the docs for more: https://nbdev.fast.ai/clean.html#clean_jupyter"), DeprecationWarning)
        jupyter_hooks = False if jupyter_hooks == 'none' else True
    else: jupyter_hooks = str2bool(jupyter_hooks)
    if jupyter_hooks: _nbdev_clean(model['content'], path=path)

# %% ../nbs/11_clean.ipynb 30
_pre_save_hook_src = '''
def nbdev_clean_jupyter(**kwargs):
    try: from nbdev.clean import clean_jupyter
    except ModuleNotFoundError: return
    clean_jupyter(**kwargs)

c.ContentsManager.pre_save_hook = nbdev_clean_jupyter'''.strip()
_pre_save_hook_re = re.compile(r'c\.(File)?ContentsManager\.pre_save_hook')

# %% ../nbs/11_clean.ipynb 31
def _add_jupyter_hooks(src, path):
    if _pre_save_hook_src in src: return
    mod = ast.parse(src)
    for node in ast.walk(mod):
        if not isinstance(node,ast.Assign): continue
        target = only(node.targets)
        if _pre_save_hook_re.match(unparse(target)):
            pre = ' '*2
            old = indent(unparse(node), pre)
            new = indent(_pre_save_hook_src, pre)
            sys.stderr.write(f"Can't install hook to '{path}' since it already contains:\n{old}\n"
                             f"Manually update to the following (without indentation) for this functionality:\n\n{new}\n\n")
            return
    src = src.rstrip()
    if src: src+='\n\n'
    return src+_pre_save_hook_src

# %% ../nbs/11_clean.ipynb 35
def _git_root(): 
    try: return Path(run('git rev-parse --show-toplevel'))
    except OSError: return None

# %% ../nbs/11_clean.ipynb 38
@call_parse
def nbdev_install_hooks():
    "Install Jupyter and git hooks to automatically clean, trust, and fix merge conflicts in notebooks"
    cfg_path = Path.home()/'.jupyter'
    cfg_path.mkdir(exist_ok=True)
    cfg_fns = [cfg_path/f'jupyter_{o}_config.py' for o in ('notebook','server')]
    for fn in cfg_fns:
        src = fn.read_text() if fn.exists() else ''
        upd = _add_jupyter_hooks(src, fn)
        if upd is not None: fn.write_text(upd)

    repo_path = _git_root()
    if repo_path is None:
        sys.stderr.write('Not in a git repository, git hooks cannot be installed.\n')
        return
    hook_path = repo_path/'.git'/'hooks'
    fn = hook_path/'post-merge'
    hook_path.mkdir(parents=True, exist_ok=True)
    fn.write_text("#!/bin/bash\nnbdev_trust")
    os.chmod(fn, os.stat(fn).st_mode | stat.S_IEXEC)

    cmd = 'git config --local include.path ../.gitconfig'
    (repo_path/'.gitconfig').write_text(f'''# Generated by nbdev_install_hooks
#
# If you need to disable this instrumentation do:
#   git config --local --unset include.path
#
# To restore:
#   {cmd}
#
[merge "nbdev-merge"]
	name = resolve conflicts with nbdev_fix
	driver = nbdev_merge %O %A %B %P
''')
    run(cmd)

    attrs_path = repo_path/'.gitattributes'
    nbdev_attr = '*.ipynb merge=nbdev-merge\n'
    try:
        attrs = attrs_path.read_text()
        if nbdev_attr not in attrs:
            if not attrs.endswith('\n'): attrs+='\n'
            attrs_path.write_text(attrs+nbdev_attr)
    except FileNotFoundError: attrs_path.write_text(nbdev_attr)

    print("Hooks are installed.")
