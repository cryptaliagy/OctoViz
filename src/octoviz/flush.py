import shutil, os
from octoviz.common import octoviz_dir

def flush(args):
    if args.flush_all:
        if args.flush_all in {'cache', 'all'}:
            shutil.rmtree(octoviz_dir('cache'), ignore_errors=True)
        if args.flush_all in {'html', 'all'}:
            shutil.rmtree(octoviz_dir('html'), ignore_errors=True)
    else:
        for repo in args.repos:
            if os.path.exists(octoviz_dir('cache/%s.json' % repo)):
                os.remove(octoviz_dir('cache/%s.json' % repo))