# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/11_test.ipynb.

# %% auto 0
__all__ = ['test_nb', 'nbdev_test']

# %% ../nbs/API/11_test.ipynb 1
import time,os,sys,traceback,contextlib, inspect
from fastcore.basics import *
from fastcore.imports import *
from fastcore.foundation import *
from fastcore.parallel import *
from fastcore.script import *
from fastcore.meta import delegates

from .config import *
from .doclinks import *
from .process import NBProcessor, nb_lang
from .frontmatter import FrontmatterProc
from logging import warning

from execnb.nbio import *
from execnb.shell import *

# %% ../nbs/API/11_test.ipynb 3
def test_nb(fn,  # file name of notebook to test
            skip_flags=None,  # list of flags marking cells to skip
            force_flags=None,  # list of flags marking cells to always run
            do_print=False,  # print completion?
            showerr=True,  # warn errors?
            basepath=None):  # path to add to sys.path
    "Execute tests in notebook in `fn` except those with `skip_flags`"
    if basepath: sys.path.insert(0, str(basepath))
    if not IN_NOTEBOOK: os.environ["IN_TEST"] = '1'
    flags=set(L(skip_flags)) - set(L(force_flags))
    nb = NBProcessor(fn, procs=FrontmatterProc, process=True).nb
    fm = getattr(nb, 'frontmatter_', {})
    if str2bool(fm.get('skip_exec', False)) or nb_lang(nb) != 'python': return True, 0

    def _no_eval(cell):
        if cell.cell_type != 'code': return True
        if 'nbdev_export'+'(' in cell.source: return True
        direc = getattr(cell, 'directives_', {}) or {}
        if direc.get('eval:', [''])[0].lower() == 'false': return True
        return flags & direc.keys()
    
    start = time.time()
    k = CaptureShell(fn)
    if do_print: print(f'Starting {fn}')
    try:
        with working_directory(fn.parent):
            k.run_all(nb, exc_stop=True, preproc=_no_eval)
            res = True
    except: 
        if showerr: warning(k.prettytb(fname=fn))
        res=False
    if do_print: print(f'- Completed {fn}')
    return res,time.time()-start

# %% ../nbs/API/11_test.ipynb 8
def _keep_file(p:Path, # filename for which to check for `indicator_fname`
               ignore_fname:str # filename that will result in siblings being ignored
                ) -> bool:
    "Returns False if `indicator_fname` is a sibling to `fname` else True"
    if p.exists(): return not bool(p.parent.ls().attrgot('name').filter(lambda x: x == ignore_fname))
    else: True

# %% ../nbs/API/11_test.ipynb 10
@call_parse
@delegates(nbglob_cli)
def nbdev_test(
    path:str=None,  # A notebook name or glob to test
    flags:str='',  # Space separated list of test flags to run that are normally ignored
    n_workers:int=None,  # Number of workers
    timing:bool=False,  # Time each notebook to see which are slow
    do_print:bool=False, # Print start and end of each notebook
    pause:float=0.01,  # Pause time (in seconds) between notebooks to avoid race conditions
    ignore_fname:str='.notest', # Filename that will result in siblings being ignored
    **kwargs):
    "Test in parallel notebooks matching `path`, passing along `flags`"
    skip_flags = get_config().tst_flags.split()
    force_flags = flags.split()
    files = nbglob(path, as_path=True, **kwargs)
    files = [f.absolute() for f in sorted(files) if _keep_file(f, ignore_fname)]
    if len(files)==0: return print('No files were eligible for testing')

    if n_workers is None: n_workers = 0 if len(files)==1 else min(num_cpus(), 8)
    os.chdir(get_config().path('nbs_path'))
    if IN_NOTEBOOK: kw = {'method':'spawn'} if os.name=='nt' else {'method':'forkserver'}
    else: kw = {}
    results = parallel(test_nb, files, skip_flags=skip_flags, force_flags=force_flags, n_workers=n_workers,
                       basepath=get_config().config_path, pause=pause, do_print=do_print, **kw)
    passed,times = zip(*results)
    if all(passed): print("Success.")
    else: 
        _fence = '='*50
        failed = '\n\t'.join(f.name for p,f in zip(passed,files) if not p)
        sys.stderr.write(f"\nnbdev Tests Failed On The Following Notebooks:\n{_fence}\n\t{failed}\n")
        sys.exit(1)
    if timing:
        for i,t in sorted(enumerate(times), key=lambda o:o[1], reverse=True): print(f"{files[i].name}: {int(t)} secs")
