# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/api/doclinks.ipynb.

# %% auto 0
__all__ = ['patch_name', 'nbglob', 'nbglob_cli', 'nbdev_export', 'NbdevLookup']

# %% ../nbs/api/doclinks.ipynb 2
from .config import *
from .maker import *
from .export import *
from .imports import *

from fastcore.script import *
from fastcore.utils import *
from fastcore.meta import delegates

import ast,contextlib
import pkg_resources,importlib
from astunparse import unparse

from pprint import pformat
from urllib.parse import urljoin
from functools import lru_cache

# %% ../nbs/api/doclinks.ipynb 5
def _sym_nm(klas, sym): return f'{unparse(klas).strip()}.{sym.name}'

def _binop_leafs(bo, o):
    "List of all leaf nodes under a `BinOp`"
    def f(b): return _binop_leafs(b, o) if isinstance(b, ast.BinOp) else [_sym_nm(b,o)]
    return f(bo.left) + f(bo.right)

def patch_name(o):
    "If `o` is decorated with `patch` or `patch_to`, return its class-prefix name"
    if not isinstance(o, (ast.FunctionDef,ast.AsyncFunctionDef)): return o.name
    d = first([d for d in o.decorator_list if decor_id(d).startswith('patch')])
    if not d: return o.name
    nm = decor_id(d)
    if nm=='patch': 
        a = o.args.args[0].annotation
        if isinstance(a, ast.BinOp): return _binop_leafs(a, o)
    elif nm=='patch_to': a = d.args[0]
    else: return o.name
    return _sym_nm(a,o)

# %% ../nbs/api/doclinks.ipynb 9
def _iter_py_cells(p):
    "Yield cells from an exported Python file."
    p = Path(p)
    cells = p.read_text().split("\n# %% ")
    for cell in cells[1:]:
        top,code = cell.split('\n', 1)
        try:
          *nb,idx = top.split()
          nb = ' '.join(nb)
        except ValueError: raise ValueError(f"Unexpected format in '{p}' at cell:\n```\n# %% {cell.strip()}.\n```\n"
                                            "The expected format is: '# %% {nb_path} {cell_idx}'.")
        nb_path = None if nb=='auto' else (p.parent/nb).resolve()  # NB paths are stored relative to .py file
        if code.endswith('\n'): code=code[:-1]
        yield AttrDict(nb=nb, idx=int(idx), code=code, nb_path=nb_path, py_path=p.resolve())

# %% ../nbs/api/doclinks.ipynb 11
def _nbpath2html(p): return p.with_name(re.sub(r'^\d+[a-zA-Z0-9]*_', '', p.name.lower())).with_suffix('.html')

# %% ../nbs/api/doclinks.ipynb 13
def _get_modidx(py_path, code_root, nbs_path):
    "Get module symbol index for a Python source file"
    cfg = get_config()
    rel_name = py_path.resolve().relative_to(code_root).as_posix()
    mod_name = '.'.join(rel_name.rpartition('.')[0].split('/'))  # module name created by py_path

    _def_types = ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef
    d = {}
    for cell in _iter_py_cells(py_path):
        if cell.nb == 'auto': continue
        loc = _nbpath2html(cell.nb_path.relative_to(nbs_path))

        def _stor(nm):
            for n in L(nm): d[f'{mod_name}.{n}'] = f'{loc.as_posix()}#{n.lower()}',rel_name
        for tree in ast.parse(cell.code).body:
            if isinstance(tree, _def_types): _stor(patch_name(tree))
            if isinstance(tree, ast.ClassDef):
                for t2 in tree.body:
                    if isinstance(t2, _def_types): _stor(f'{tree.name}.{t2.name}')
    return {mod_name: d}

# %% ../nbs/api/doclinks.ipynb 15
def _build_modidx(dest=None, nbs_path=None, skip_exists=False):
    "Create _modidx.py"
    if dest is None: dest = get_config().lib_path
    if not Path(dest).exists(): return
    nbs_path = Path(nbs_path or get_config().nbs_path).resolve()
    if os.environ.get('IN_TEST',0): return
    idxfile = dest/'_modidx.py'
    if skip_exists and idxfile.exists(): return
    with contextlib.suppress(FileNotFoundError): idxfile.unlink()
    if idxfile.exists(): res = exec_local(idxfile.read_text(), 'd')
    else: res = dict(syms={}, settings={}) 
    res['settings'] = {k:v for k,v in get_config().d.items()
                       if k in ('doc_host','doc_baseurl','lib_path','git_url','branch')}
    code_root = dest.parent.resolve()
    for file in globtastic(dest, file_glob="*.py", skip_file_re='^_', skip_folder_re="\.ipynb_checkpoints"):
        res['syms'].update(_get_modidx((dest.parent/file).resolve(), code_root, nbs_path=nbs_path))
    idxfile.write_text("# Autogenerated by nbdev\n\nd = "+pformat(res, width=140, indent=2, compact=True)+'\n')

# %% ../nbs/api/doclinks.ipynb 20
@delegates(globtastic)
def nbglob(path=None, skip_folder_re = '^[_.]', file_glob='*.ipynb', skip_file_re='^[_.]', key='nbs_path', as_path=False, **kwargs):
    "Find all files in a directory matching an extension given a config key."
    path = Path(path or get_config()[key])
    recursive=get_config().recursive
    res = globtastic(path, file_glob=file_glob, skip_folder_re=skip_folder_re,
                     skip_file_re=skip_file_re, recursive=recursive, **kwargs)
    return res.map(Path) if as_path else res

# %% ../nbs/api/doclinks.ipynb 21
def nbglob_cli(
    path:str=None, # Path to notebooks
    symlinks:bool=False, # Follow symlinks?
    file_glob:str='*.ipynb', # Only include files matching glob
    file_re:str=None, # Only include files matching regex
    folder_re:str=None, # Only enter folders matching regex
    skip_file_glob:str=None, # Skip files matching glob
    skip_file_re:str='^[_.]', # Skip files matching regex
    skip_folder_re:str = '^[_.]'): # Skip folders matching regex
    "Find all files in a directory matching an extension given a config key."
    return nbglob(path, symlinks=symlinks, file_glob=file_glob, file_re=file_re, folder_re=folder_re,
                  skip_file_glob=skip_file_glob, skip_file_re=skip_file_re, skip_folder_re=skip_folder_re)

# %% ../nbs/api/doclinks.ipynb 22
@call_parse
@delegates(nbglob_cli)
def nbdev_export(
    path:str=None, # Path or filename
    **kwargs):
    "Export notebooks in `path` to Python modules"
    if os.environ.get('IN_TEST',0): return
    files = nbglob(path=path, as_path=True, **kwargs).sorted('name')
    for f in files: nb_export(f)
    add_init(get_config().lib_path)
    _build_modidx()

# %% ../nbs/api/doclinks.ipynb 24
import importlib,ast
from functools import lru_cache

# %% ../nbs/api/doclinks.ipynb 25
def _find_mod(mod):
    mp,_,mr = mod.partition('/')
    spec = importlib.util.find_spec(mp)
    if not spec: return
    loc = Path(spec.origin).parent
    return loc/mr

@lru_cache(None)
def _get_exps(mod):
    mf = _find_mod(mod)
    if not mf: return {}
    txt = mf.read_text()
    _def_types = ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef
    d = {}
    for tree in ast.parse(txt).body:
        if isinstance(tree, _def_types):
            for t in L(patch_name(tree)): d[t] = tree.lineno
        if isinstance(tree, ast.ClassDef): d.update({tree.name+"."+t2.name: t2.lineno for t2 in tree.body if isinstance(t2, _def_types)})
    return d

def _lineno(sym, fname): return _get_exps(fname).get(sym, None) if fname else None

# %% ../nbs/api/doclinks.ipynb 27
def _qual_sym(s, settings):
    if not isinstance(s,tuple): return s
    nb,py = s
    nbbase = urljoin(settings["doc_host"]+'/',settings["doc_baseurl"])
    nb = urljoin(nbbase+'/', nb)
    gh = urljoin(settings["git_url"]+'/', f'blob/{settings["branch"]}/{py}')
    return nb,py,gh

def _qual_mod(mod_d, settings): return {sym:_qual_sym(s, settings) for sym,s in mod_d.items()}
def _qual_syms(entries):
    settings = entries['settings']
    if 'doc_host' not in settings: return entries
    return {'syms': {mod:_qual_mod(d, settings) for mod,d in entries['syms'].items()}, 'settings':settings}

# %% ../nbs/api/doclinks.ipynb 28
_re_backticks = re.compile(r'`([^`\s]+)`')

# %% ../nbs/api/doclinks.ipynb 29
@lru_cache(None)
class NbdevLookup:
    "Mapping from symbol names to docs and source URLs"
    def __init__(self, strip_libs=None, incl_libs=None, skip_mods=None):
        cfg = get_config()
        if strip_libs is None:
            try: strip_libs = cfg.get('strip_libs', cfg.get('lib_path', 'nbdev').name).split()
            except FileNotFoundError: strip_libs = 'nbdev'
        skip_mods = setify(skip_mods)
        strip_libs = L(strip_libs)
        if incl_libs is not None: incl_libs = (L(incl_libs)+strip_libs).unique()
        # Dict from lib name to _nbdev module for incl_libs (defaults to all)
        self.entries = {o.name: _qual_syms(o.resolve()) for o in list(pkg_resources.iter_entry_points(group='nbdev'))
                       if incl_libs is None or o.dist.key in incl_libs}
        py_syms = merge(*L(o['syms'].values() for o in self.entries.values()).concat())
        for m in strip_libs:
            if m in self.entries:
                _d = self.entries[m]
                stripped = {remove_prefix(k,f"{mod}."):v
                            for mod,dets in _d['syms'].items() if mod not in skip_mods
                            for k,v in dets.items()}
                py_syms = merge(stripped, py_syms)
        self.syms = py_syms

    def __getitem__(self, s): return self.syms.get(s, None)

    def doc(self, sym):
        "Link to docs for `sym`"
        res = self[sym]
        return res[0] if isinstance(res, tuple) else res

    def code(self, sym):
        "Link to source code for `sym`"
        res = self[sym]
        if not isinstance(res, tuple): return None
        _,py,gh = res
        line = _lineno(sym, py)
        return f'{gh}#L{line}'

    def _link_sym(self, m):
        l = m.group(1)
        s = self.doc(l)
        if s is None: return m.group(0)
        l = l.replace('\\', r'\\')
        return rf"[`{l}`]({s})"

    def link_line(self, l): return _re_backticks.sub(self._link_sym, l)

    def linkify(self, md):
        if md:
            in_fence=False
            lines = md.splitlines()
            for i,l in enumerate(lines):
                if l.startswith("```"): in_fence=not in_fence
                elif not l.startswith('    ') and not in_fence: lines[i] = self.link_line(l)
            return '\n'.join(lines)
