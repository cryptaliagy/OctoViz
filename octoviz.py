import github3, arrow
import os, sys, datetime, argparse, json, re, shutil
import itertools
from pathlib import Path
from bokeh.plotting import figure, output_file, show
from bokeh.layouts import gridplot, row
from bokeh.palettes import Category10 as palette
from functools import reduce
import pandas as pd

def make_github_client(token, url=None):
    try:
        if url:
            client = github3.enterprise_login(token=token, url=url)
        else:
            client = github3.login(token=token)

        if client is None:
            raise(Exception())
    except:
        sys.stderr.write("\nError performing login to Github!\n")
        sys.stderr.write("Check the token or url for login\n\n")
        sys.exit(1)

def get_raw_pull_data(client, organization, repository):
    try:
        repo = client.repository(organization, repository)
    except:
        sys.stderr.write('Error trying to fetch repo %s/%s, skipping...' % (organization, repository))
        return None
    pull_requests = repo.pull_requests(state='closed')

    result = list(map(lambda x: x.as_dict(), pull_requests))
    return result


def data_to_graph_params(data, width, name_map):
    def colors():
        yield from itertools.cycle(palette[10])
        
    color = colors()
    line_result = {}
    bar_result = {}
    for param in data:
        match = re.match('(1?[0-9]?[0-9])th', param)
        x = []
        y = []
        for key in sorted(data[param].keys()):
            x.append(key)
            y.append(data[param][key])
        if match:
            line_result[param] = {
                'legend': "{}%-tile time".format(match[1]),
                'line_color': next(color),
                'x': x,
                'y': y
            }
        else:
            bar_result[param] = {
                'width': width,
                'legend': name_map[param],
                'x': x,
                'top': y,
                'fill_color': next(color)
            }
    return line_result, bar_result


def graph(line_data, bar_data, repository_name, frame, grouped, x_range=None, y_range=None):
    line_chart = figure(
        title="Pull Request Data for %s, Aggregated by %s %s" % (repository_name.capitalize(), frame.capitalize(), grouped.capitalize()),
        x_axis_label="Date", 
        y_axis_label='Time to close PR (days)', 
        x_axis_type="datetime")
    if x_range is not None:
        line_chart.x_range = x_range
    if y_range is not None:
        line_chart.y_range = y_range

    bar_chart = figure(
        title="Pull Request Data for %s, Aggregated by %s %s" % (repository_name.capitalize(), frame.capitalize(), grouped.capitalize()), 
        x_axis_label='Date', 
        x_axis_type="datetime", 
        x_range=line_chart.x_range)
    
    for key in line_data.keys():
        line_chart.line(line_width=2, **line_data[key])
    
    for key in bar_data.keys():
        bar_chart.vbar(**bar_data[key])
    
    line_chart.legend.click_policy = 'hide'

    return [line_chart, bar_chart]

def run(args, octoviz_dir):
    if args.token_value:
        token = args.token_value
    elif args.token_env_name:
        token = os.getenv(args.token_env_name)
    else:
        token = os.getenv('GITHUB_API_TOKEN')
    
    if args.url:
        url = args.url
    if args.github:
        url = None
    else:
        url = os.getenv('GITHUB_URL')
        
    client = make_github_client(token, url)

    stat_percentiles = sorted([int(p) for p in args.percentiles.split(',')])

    pull_data = []
    chart_data = []
    x_axis = None
    y_axis = None
    frame_data = lambda func, iterable: list(map(func, iterable))
    stats = lambda group: {'count': group.count(), **{'%dth' % d: group.quantile(d/100) for d in stat_percentiles}}

    build_cache_flags = args.fetch_no_cache or args.force_build_cache

    if args.name:
        file_name = octoviz_dir('html/%s.html' % args.name[0])
    else:
        file_name = octoviz_dir('html/octoviz.html')
    
    if not args.force_build_cache == 'no-render':
        if not os.path.exists(octoviz_dir('html')):
            os.mkdir(octoviz_dir('html'))
        output_file(file_name)

    for repository in args.repos:
        org, repo = repository.split('/') 

        # Build cache if force or if the cache does not exist
        if build_cache_flags or not os.path.exists(octoviz_dir('cache/%s/%s.json' % (org, repo))):
            if not os.path.exists(octoviz_dir('cache')):
                os.mkdir(octoviz_dir('cache'))
            if not os.path.exists(octoviz_dir('cache/%s' % org)):
                os.mkdir(octoviz_dir('cache/%s' % org))

            pull_data = get_raw_pull_data(client, org, repo)
            if pull_data is None:
                continue

            
            if not args.fetch_no_cache:
                with open(octoviz_dir('cache/%s.json' % repository), "w") as f:
                    json.dump(pull_data, f)
                
                if args.no_render:
                    continue

        # Read from cache files if they exist and not force-rebuild
        else:
            with open(octoviz_dir('cache/%s.json' % repository), "r") as f:
                pull_data = json.load(f)
        
        # Build pandas frame
        frame = pd.DataFrame(
            {
                'pull number': frame_data(lambda x: x['number'], pull_data),
                'created': frame_data(lambda x: arrow.get(x['created_at']).floor(args.frame).datetime, pull_data),
                'closed': frame_data(lambda x: arrow.get(x['closed_at']).floor(args.frame).datetime, pull_data),
                'user': frame_data(lambda x: x['user']['login'], pull_data),
                'lifetime': frame_data(lambda x: (arrow.get(x['closed_at']) - arrow.get(x['created_at'])).total_seconds()/3600/24, pull_data)
            }
        )
        
        bar_width = (arrow.now().ceil(args.frame) - arrow.now().floor(args.frame)).total_seconds() * 800
        data = frame['lifetime'].groupby(frame[args.group]).apply(stats).unstack().to_dict()
        line, bar = data_to_graph_params(data, bar_width, {'count': 'PRs Completed'})
        chart_data.append(graph(line, bar, repo, args.frame, args.group, x_axis, y_axis))

        if args.link_x:
            x_axis = chart_data[-1][0].x_range
        if args.link_y:
            y_axis = chart_data[-1][0].y_range

    
    if args.remove:
        shutil.rmtree(octoviz_dir('cache'), ignore_errors=True)

    if not args.no_render:
        show(gridplot(chart_data))

def flush(args, octoviz_dir):
    if args.flush_all:
        if args.flush_all in {'cache', 'all'}:
            shutil.rmtree(octoviz_dir('cache'), ignore_errors=True)
        if args.flush_all in {'html', 'all'}:
            shutil.rmtree(octoviz_dir('html'), ignore_errors=True)
    else:
        for repo in args.repos:
            if os.path.exists(octoviz_dir('cache/%s.json' % repo)):
                os.remove(octoviz_dir('cache/%s.json' % repo))

def cli():
    home_dir = str(Path.home())
    octoviz_dir = lambda x="": '%s/.octoviz%s' % (home_dir, "/%s" % x if x else "")

    main_parser = argparse.ArgumentParser(description='A tool to visualize Github data')
    sub_parsers = main_parser.add_subparsers(help="")
    flush_parser = sub_parsers.add_parser('flush', help="Flush the cached or created files", description='Sub-tool to flush cached and rendered files')
    parser = sub_parsers.add_parser('run', help="Run the OctoViz", description='Creates graphs of Pull Request lifecycle data')

    flush_parser.add_argument('-f', '--flush-all', action='store', nargs='?', default=False, const='all',
        choices=['cache', 'html', 'all'], help='Flushes all cached data and html files by default, or one of them if specified')
    flush_parser.add_argument('repos', metavar='repository', nargs='*', default=[], help="Repositories to flush from the cache")

    parser.add_argument('-m', '--month', dest='frame', action='store_const', const='month', default='week', help='aggregate data by month (default: by week)')
    cache_group = parser.add_mutually_exclusive_group()
    url_group = parser.add_mutually_exclusive_group()
    token_group = parser.add_mutually_exclusive_group()

    cache_group.add_argument('-b', '--build-cache', dest='force_build_cache', action='store_true', help='Force build the cache, overriding any currently cached data.')
    cache_group.add_argument('--no-cache', dest='fetch_no_cache', action='store_true', help='Force fetch the data but do not write it to a local cache')
    
    url_group.add_argument('-u', '--url', action='store', help='The url to use (if in a corporate environment)')
    url_group.add_argument('-g', '--github', action='store_true', help='Force connect to Github\'s servers instead of any set by environment variable')

    token_group.add_argument('-v', '--token-value', action='store', help='OAuth token to use (overrides environment-specified token)')
    token_group.add_argument('-e', '--token-env-name', action='store', help='Specify the name of the environment variable to use for the token')
    
    parser.add_argument('--no-render', action='store_true', help='Prevent OctoViz from generating HTML file')
    parser.add_argument('-c', '--cleanup', action='store_true', help='Flushes all cached data after execution. Does not delete html files.')
    parser.add_argument('-x', '--link-x-axis', dest='link_x', action='store_true', help='Link the x-axis of all generated graphs')
    parser.add_argument('-y', '--link-y-axis', dest='link_y', action='store_true', help='Link the y-axis of all line graphs')
    parser.add_argument('-n', '--name', action='store', help='Name of the output file')

    parser.add_argument('--group-by', dest='group', choices=['created', 'closed'], default='closed', nargs='?', help='What metric to group the data by. Default is \'closed\'')
    parser.add_argument('repos', metavar='repository', nargs='+', default=[], help='Repository to pull data from')

    parser.add_argument('-p', '--percentiles', type=str, default='25,50,90', help="A comma delimited list of percentiles to render data for")

    parser.epilog = 'All files are stored under ~/.octoviz directory. If no output file name has been specified, OctoViz will override previous render'

    parser.set_defaults(func=lambda args: run(args, octoviz_dir))
    flush_parser.set_defaults(func=lambda args: flush(args, octoviz_dir))

    args = main_parser.parse_args()

    if not os.path.exists(octoviz_dir()):
        os.mkdir(octoviz_dir())

    args.func(args)



if __name__ == "__main__":
    cli()
    