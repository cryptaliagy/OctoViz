import github3, arrow
import os, sys, datetime, argparse, json, re, shutil
import itertools
from pathlib import Path
from bokeh.plotting import figure, output_file, show
from bokeh.layouts import gridplot, row
from bokeh.palettes import Category10 as palette
from functools import reduce
import pandas as pd

# Global constants
home_dir = str(Path.home())
octoviz_dir = lambda x="": '%s/.octoviz%s' % (home_dir, "/%s" % x if x else "")
clients = []



def configuration():
    main_parser = argparse.ArgumentParser(description='A tool to visualize Github data')
    sub_parsers = main_parser.add_subparsers(help="")

    flush_parser = sub_parsers.add_parser('flush', help='Flush the cached or created files', description='Sub-tool to flush cached and rendered files')
    parser = sub_parsers.add_parser('run', help='Run the OctoViz', description='Creates graphs of Pull Request lifecycle data')
    profile_parser = sub_parsers.add_parser('profile', help='Create, edit, or save OctoViz Github profiles', description='Create, edit, or save OctoViz Github profiles')

    profile_sub_parsers = profile_parser.add_subparsers(help="")

    profile_create_parser = profile_sub_parsers.add_parser('create', help='Create a new OctoViz profile',
        description='''Create a new OctoViz profile!\n
        OctoViz profiles determine the Github server and the API token that will be used when OctoViz is run''')
    profile_delete_parser = profile_sub_parsers.add_parser('delete', help='Delete OctoViz profiles', description='''Delete OctoViz profiles by specifying the names of the profiles to delete''')
    profile_update_parser = profile_sub_parsers.add_parser('update', help='Update an OctoViz profile', description='Update information on an OctoViz profile')

    profile_update_parser.add_argument('name', metavar='NAME', help='The name of the profile to update')
    profile_update_parser.add_argument('-t', '--token', help='The new token to use for the profile')
    profile_update_parser.add_argument('-u', '--url', nargs='?', default=False, const=None, help='The new URL to connect with. Specify no argument if switching to public Github server')

    profile_delete_parser.add_argument('profile_names', metavar='NAME', nargs='+', help='The name of the profile(s) to be deleted')

    profile_create_parser.add_argument('-u', '--url', action='store', help='The URL for the server OctoViz should use. Include only if using an Enterprise server')
    profile_create_parser.add_argument('-n', '--name', action='store', help='The name of the profile to be created (default: \'default\')', default='default')
    profile_create_parser.add_argument('-t', '--token', action='store', help='The token OctoViz should use to authenticate to the server', required=True)

    profile_parser.add_argument('-l', '--list', action='store_true', help='List all available profiles')

    flush_parser.add_argument('-f', '--flush-all', action='store', nargs='?', default=False, const='all',
        choices=['cache', 'html', 'all'], help='Flushes all cached data and html files by default, or one of them if specified')
    flush_parser.add_argument('repos', metavar='repository', nargs='*', default=[], help="Repositories to flush from the cache")

    parser.add_argument('-m', '--month', dest='frame', action='store_const', const='month', default='week', help='aggregate data by month (default: by week)')
    cache_group = parser.add_mutually_exclusive_group()
    limit_group = parser.add_mutually_exclusive_group()

    cache_group.add_argument('-b', '--build-cache', dest='force_build_cache', action='store_true', help='Force build the cache, overriding any currently cached data.')
    cache_group.add_argument('--no-cache', dest='fetch_no_cache', action='store_true', help='Force fetch the data but do not write it to a local cache')

    limit_group.add_argument('--no-limit', action='store_true', help='Retrieve all PR data from the repository. (default: 12 months)')
    limit_group.add_argument('--limit-by-weeks', metavar='N', action='store', type=int, help='Limit fetching to only PRs that have been created since N months ago (default: 12 months)')
    limit_group.add_argument('--limit-by-months', metavar='N', action='store', type=int, help='Limit fetching to only PRs that have been created since N months ago. (default: 12 months)')
    
    parser.add_argument('--no-render', action='store_true', help='Prevent OctoViz from generating HTML file')
    parser.add_argument('-c', '--cleanup', action='store_true', help='Flushes all cached data after execution. Does not delete html files.')
    parser.add_argument('-x', '--link-x-axis', dest='link_x', action='store_true', help='Link the x-axis of all generated graphs')
    parser.add_argument('-y', '--link-y-axis', dest='link_y', action='store_true', help='Link the y-axis of all line graphs')
    parser.add_argument('-n', '--name', action='store', help='Name of the output file')
    parser.add_argument('--complete', action='store_true', help="Display only complete data (does not display current week/month's data)")
    parser.add_argument('-p', '--percentiles', type=str, default='25,50,90', help="A comma delimited list of percentiles to render data for")

    parser.add_argument('--group-by', dest='group', choices=['created', 'closed'], default='closed', nargs='?', help='What metric to group the data by. Default is \'closed\'')
    parser.add_argument('repos', metavar='repository', nargs='+', default=[], help='Repository to pull data from')

    parser.epilog = 'All files are stored under ~/.octoviz directory. If no output file name has been specified, OctoViz will override previous render'

    # Attach the parsers to the right functions
    parser.set_defaults(func=run)
    flush_parser.set_defaults(func=flush)
    profile_parser.set_defaults(func=profile_list)
    profile_delete_parser.set_defaults(func=profile_delete)
    profile_update_parser.set_defaults(func=lambda args: profile_create_update(args, False))
    profile_create_parser.set_defaults(func=lambda args: profile_create_update(args, True))

    return main_parser


def load_profile(name):
    if name[-8:] == '.profile':
        path = octoviz_dir('profiles/%s' % name)
    else:
        path = octoviz_dir('profiles/%s.profile' % name)
    if not os.path.exists(path):
        sys.stderr.write('Profile does not exist!\n')
        sys.exit(1)

    with open(path, 'r') as f:
        profile = json.load(f)
    
    return profile


def write_profile(profile):
    name = profile['name']
    path = octoviz_dir('profiles/%s.profile' % name)

    with open(path, 'w') as f:
        json.dump(profile, f)


def get_all_profiles():
    path = octoviz_dir('profiles/')
    if not os.path.exists(path):
        return []
    _, _, profiles = next(os.walk(path))

    return profiles

    
def make_github_client(profile):
    token = profile['token']
    url = profile['url']
    try:
        if url:
            client = github3.enterprise_login(token=token, url=url)
        else:
            client = github3.login(token=token)

        if client is None:
            raise(Exception())
    except Exception as e:
        sys.stderr.write("\nError performing login to Github!\n")
        sys.stderr.write("Check the token or url for login of profile %s\n\n" % profile['name'])
        raise(e)  ## Re-raise the exception to handle it somewhere else in the stack
    
    return client


def create_directory(dir):
    exists = []
    create = dir.split('/')

    for di in create:
        path = '/'.join(exists + [di])
        if not os.path.exists(octoviz_dir(path)):
            os.mkdir(octoviz_dir(path))
        exists.append(di)


def get_raw_pull_data(organization, repository, rate_limit):
    if rate_limit:
        frame = rate_limit[0][:-1]
        shift = {rate_limit[0]: rate_limit[1]}
        limited = arrow.now().shift(**shift).floor(frame)
    else:
        limited = None
    repo = None
    for client in clients:
        try:
            repo = client.repository(organization, repository)
            break  # Found the repo, stop searching
        except github3.exceptions.NotFoundError as e:
            continue  # Try the next client
        except Exception as e:
            sys.stderr.write('Error trying to fetch repo %s/%s, skipping...\n' % (organization, repository))
            return None
    
    if repo is None:
        return None  # Can't find it under any of the profiles, return None
    pull_requests = repo.pull_requests(state='closed')

    result = []
    for pull_request in pull_requests:
        if limited is not None and arrow.get(pull_request.created_at).floor(frame) <= limited:
            break

        try:
            pull_dict = pull_request.as_dict()
        except:
            continue
        
        result.append(pull_dict)

    return result


def data_to_graph_params(data, width, name_map, skip_last=False):
    def colors():
        yield from itertools.cycle(palette[10])
        
    color = colors()
    line_result = {}
    bar_result = {}
    end_index = -1 if skip_last else None
    for param in data:
        match = re.match('(1?[0-9]?[0-9])th', param)
        x = []
        y = []
        for key in sorted(data[param].keys())[:end_index]:
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


def run(args):
    profiles = map(lambda x: load_profile(x), get_all_profiles())

    for profile in profiles:
        try:
            clients.append(make_github_client(profile))
        except Exception:
            pass  # Ignore the faulty profile but continue execution
    
    if args.complete:
        modifier = -1
    else:
        modifier = 0

    if args.no_limit:
        rate_limit = None
    elif args.limit_by_weeks:
        if args.month:
            sys.stderr.write('Cannot limit by weeks when aggregating by month!\n')
            sys.exit(1)
        rate_limit = ('weeks', -args.limit_by_weeks+modifier)
    elif args.limit_by_months:
        rate_limit = ('months', -args.limit_by_months+modifier)
    else:
        rate_limit = ('months', -12)

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
        create_directory('html')
        output_file(file_name)

    for repository in args.repos:
        org, repo = repository.split('/') 

        # Build cache if force or if the cache does not exist
        if build_cache_flags or not os.path.exists(octoviz_dir('cache/%s/%s.json' % (org, repo))):
            create_directory('cache/%s' % org)

            pull_data = get_raw_pull_data(org, repo, rate_limit)
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
        line, bar = data_to_graph_params(data, bar_width, {'count': 'PRs Completed'}, args.complete)
        chart_data.append(graph(line, bar, repo, args.frame, args.group, x_axis, y_axis))

        if args.link_x:
            x_axis = chart_data[-1][0].x_range
        if args.link_y:
            y_axis = chart_data[-1][0].y_range

    if args.cleanup:
        shutil.rmtree(octoviz_dir('cache'), ignore_errors=True)

    if not args.no_render and len(chart_data) > 0:
        show(gridplot(chart_data))


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


def profile_create_update(args, create):
    path = octoviz_dir('profiles/%s.profile' % args.name)
    if not os.path.exists(path) ^ create:
        sub_tool = 'update' if create else 'create'
        exists = 'already exists' if create else 'does not exist'
        sys.stderr.write('This profile %s! Did you mean to use `octoviz %s` instead?\n' % (exists, sub_tool))
        sys.exit(1)

    doing = 'creating' if create else 'updating'
    done = 'created' if create else 'updated'

    if create:
        profile = { 'name': args.name, 'token': args.token, 'url': args.url }
    else:
        profile = load_profile(args.name)
        if args.token:
            profile['token'] = args.token
        
        if args.url is not False:
            profile['url'] = args.url

    try:
        sys.stdout.write('Attempting to login to Github server to check credentials...\n')
        client = make_github_client(profile)
    except Exception as e:
        sys.stderr.write('Error %s profile! Aborting...\n' % doing)
        sys.exit(1)
    
    sys.stdout.write('Login successful! %s profile...\n' % (doing.capitalize()))
    create_directory('profiles')

    write_profile(profile)

    sys.stdout.write('Successfully %s profile with name \'%s\'\n\n' % (done, args.name))


def profile_delete(args):
    for profile in args.profile_names:
        path = octoviz_dir('profiles/%s.profile' % profile)
        if os.path.exists(path):
            os.remove(path)
        else:
            sys.stderr.write('Profile \'%s\' does not exist\n' % profile)


def profile_list(args):
    path = octoviz_dir('profiles')
    if not args.list or not os.path.exists(path):
        return
    files = get_all_profiles()

    for f in files:
        match = re.match('(.+)\.profile', f)
        if match:
            sys.stdout.write('- %s\n' % match[1])
    

def cli():
    create_directory('')  # Create the OctoViz directory if it does not exist

    args = configuration().parse_args()

    args.func(args)


if __name__ == "__main__":
    cli()
    