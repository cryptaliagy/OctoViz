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
    profile_parser = sub_parsers.add_parser('profile', help='Create, edit, or save OctoViz Github profiles', 
        description='Create, edit, or save OctoViz Github profiles')

    profile_sub_parsers = profile_parser.add_subparsers(help="")

    profile_create_parser = profile_sub_parsers.add_parser('create', help='Create a new OctoViz profile',
        description='''Create a new OctoViz profile!\n
        OctoViz profiles determine the Github server and the API token that will be used when OctoViz is run''')
    profile_delete_parser = profile_sub_parsers.add_parser('delete', help='Delete OctoViz profiles', 
        description='''Delete OctoViz profiles by specifying the names of the profiles to delete''')
    profile_update_parser = profile_sub_parsers.add_parser('update', help='Update an OctoViz profile',
        description='Update information on an OctoViz profile')

    profile_update_parser.add_argument('name', metavar='NAME', help='The name of the profile to update')
    profile_update_parser.add_argument('-t', '--token', help='The new token to use for the profile')
    profile_update_parser.add_argument('-u', '--url', nargs='?', default=False, const=None,
        help='The new URL to connect with. Specify no argument if switching to public Github server')

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
    aggre_group = parser.add_mutually_exclusive_group()
    compr_group = parser.add_mutually_exclusive_group()

    cache_group.add_argument('-b', '--build-cache', dest='force_build_cache', action='store_true', 
        help='Force build the cache, overriding any currently cached data.')
    cache_group.add_argument('--no-cache', dest='fetch_no_cache', action='store_true', help='Force fetch the data but do not write it to a local cache')

    limit_group.add_argument('--no-limit', action='store_true', help='Retrieve all PR data from the repository. (default: 12 months)')
    limit_group.add_argument('--limit-by-weeks', metavar='N', action='store', type=int, 
        help='Limit fetching to only PRs that have been created since N months ago (default: 12 months)')
    limit_group.add_argument('--limit-by-months', metavar='N', action='store', type=int, 
        help='Limit fetching to only PRs that have been created since N months ago. (default: 12 months)')
    
    parser.add_argument('--full', action='store_true', 
        help='Grabs the full Pull Request data for more thorough data processing (grouping by additions/deletions/total). WARNING: this will take a long time')
    parser.add_argument('--no-render', action='store_true', help='Prevent OctoViz from generating HTML file')
    parser.add_argument('--cleanup', action='store_true', help='Flushes all cached data after execution. Does not delete html files.')
    parser.add_argument('-x', '--link-x-axis', dest='link_x', action='store_true', help='Link the x-axis of all generated graphs')
    parser.add_argument('-y', '--link-y-axis', dest='link_y', action='store_true', help='Link the y-axis of all line graphs')
    parser.add_argument('-n', '--name', action='store', help='Name of the output file')
    parser.add_argument('--complete', action='store_true', help="Display only complete data (does not display current week/month's data)")
    parser.add_argument('-p', '--percentiles', type=str, default='25,50,90', help="A comma delimited list of percentiles to render data for")

    aggre_group.add_argument('--group-by', dest='group', choices=['created', 'closed'], 
        default='closed', nargs='?', help='What metric to group the data by. Default is \'closed\'.')
    aggre_group.add_argument('--analyze-by', dest='analyze', choices=['additions', 'deletions', 'total'], 
        help='Line change metric to group data by. Requires that data be scrapped or cached in full, will error otherwise')
    compr_group.add_argument('--compare-current', dest='compare_current', choices=['week', 'month', 'quarter', 'year'], 
        help='''Render two sets of graphs for each repository comparing the current selected time period to the one before it. 
        Can only be used in conjuction with --analyze-by.''')
    compr_group.add_argument('--compare-last', dest='compare_last', choices=['week', 'month', 'quarter', 'year'],
        help='''Render two sets of graphs for each repository comparing the previous selected time period to the one before it.
        Can only be used in conjuction with --analyze-by.''')
    parser.add_argument('--round-to', type=int, default=20, 
        help='The number of lines to round to. Can only be used in conjunction with --analyze-by. Default is 20')
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


def get_raw_pull_data(organization, repository, rate_limit, full):
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
        except Exception as e:
            continue  # Try the next client
    
    if repo is None:
        return None  # Can't find it under any of the profiles, return None
    pull_requests = repo.pull_requests(state='closed')

    result = []
    for pull_request in pull_requests:
        if limited is not None and arrow.get(pull_request.created_at).floor(frame) <= limited:
            break

        try:
            if full:
                pull_dict = repo.pull_request(pull_request.number).as_dict()  # Get the full data
            else:
                pull_dict = pull_request.as_dict()
        except Exception as e:
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


def graph(line_data, bar_data, repository_name, frame, grouped, x_range=None, y_range=None, bar_y_range=None, is_datetime=True, custom_title = ""):
    axis_type = 'datetime' if is_datetime else 'linear'
    time = frame if is_datetime else 'lines changed -'
    if custom_title:
        title = custom_title
    else:
        title = "Pull Request Data for %s, Aggregated by %s %s" % (repository_name.capitalize(), time.capitalize(), grouped.capitalize())
    line_chart = figure(
        title=title,
        x_axis_label="Date" if is_datetime else "Number of lines", 
        y_axis_label='Time to close PR (days)',
        x_axis_type=axis_type)

    if x_range is not None:
        line_chart.x_range = x_range
    if y_range is not None:
        line_chart.y_range = y_range

    bar_chart = figure(
        title=title, 
        x_axis_label='Date' if is_datetime else 'Number of Lines',
        x_range=line_chart.x_range,
        x_axis_type=axis_type)
    
    if bar_y_range is not None:
        bar_chart.y_range = bar_y_range
    
    for key in line_data.keys():
        line_chart.line(line_width=2, **line_data[key])
        line_chart.circle(size=5, **line_data[key])
    
    for key in bar_data.keys():
        bar_chart.vbar(**bar_data[key])
    
    line_chart.legend.click_policy = 'hide'

    return [line_chart, bar_chart]


def get_rate_limit(args):
    if args.complete:
        modifier = -1
    else:
        modifier = 0
    
    if args.no_limit:
        return None
    elif args.compare_current:
        time_frame = args.compare_current + 's'
        limit_factor = -2  # Current + previous
    elif args.compare_last:
        time_frame = args.compare_last + 's'
        limit_factor = -3  # Current + last 2 previous, filter later
    elif args.limit_by_weeks:
        if args.frame == 'month':
            sys.stderr.write('Cannot limit by weeks when aggregating by month!\n')
            sys.exit(1)
        time_frame = 'weeks'
        limit_factor = -args.limit_by_weeks+modifier
    elif args.limit_by_months:
        time_frame = 'months'
        limit_factor = -args.limit_by_months+modifier
        if args.frame == 'week':
            limit_factor *= 4
    else:
        time_frame = 'months'
        limit_factor = -12+modifier

    return (time_frame, limit_factor)

def clients_from_profiles():
    profiles = map(lambda x: load_profile(x), get_all_profiles())
    for profile in profiles:
        try:
            clients.append(make_github_client(profile))  # Add to the global space client list for shared access
        except Exception:
            sys.stderr.write('Error connecting to client from profile %s, skipping...\n' % profile['name'])
    
def custom_percentiles(args):
    return sorted([int(p) for p in args.percentiles.split(',')])


def run(args):
    clients_from_profiles()
    
    modifier = 0 if args.complete else -1

    rate_limit = get_rate_limit(args)

    stat_percentiles = custom_percentiles(args)

    pull_data = []
    chart_data = []
    x_axis = None
    y_axis = None
    num_prs_y_axis = None
    stats = lambda group: {'count': group.count(), **{'%dth' % d: group.quantile(d/100) for d in stat_percentiles}}

    build_cache_flags = args.fetch_no_cache or args.force_build_cache

    if args.analyze:
        group = args.analyze
    else:
        group = args.group

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

            pull_data = get_raw_pull_data(org, repo, rate_limit, args.full)
            if pull_data is None:
                sys.stderr.write('Could not find repository %s, skipping...\n' % repository)
                continue

            full = args.full

            dump = {'full': full, 'data':pull_data}

            if not args.fetch_no_cache:
                with open(octoviz_dir('cache/%s.json' % repository), "w") as f:
                    json.dump(dump, f)
                
                if args.no_render:
                    continue

        # Read from cache files if they exist and not force-rebuild
        else:
            with open(octoviz_dir('cache/%s.json' % repository), "r") as f:
                dump = json.load(f)
                pull_data = dump['data']
                full = dump['full']

        rounded = lambda x: x - (x % args.round_to)
        frame_data = lambda func: list(map(func, pull_data))
        is_datetime = args.analyze is None

        if args.analyze and not full:
            sys.stderr.write('When trying to use line change analyze tool, full-data scrapping is required. Rebuild the cache with --full flag and try again')
            sys.exit(1)
        
        # Optimizing by only doing one of these per request
        if group == 'closed':
            framed_data = frame_data(lambda x: arrow.get(x['closed_at']).floor(args.frame).datetime)
        elif group == 'additions':
            framed_data = frame_data(lambda x: rounded(x['additions']))
        elif group == 'deletions':
            framed_data = frame_data(lambda x: rounded(x['deletions']))
        elif group == 'total':
            framed_data = frame_data(lambda x: rounded(x['additions'] + x['deletions']))
        else:  # Default to fall back to
            group = 'closed'
            framed_data = frame_data(lambda x: arrow.get(x['closed_at']).floor(args.frame).datetime)

        # Build pandas frame
        dataframe_dict = {
            'pull number': frame_data(lambda x: x['number']),
            'lifetime': frame_data(lambda x: (arrow.get(x['closed_at']) - arrow.get(x['created_at'])).total_seconds()/3600/24),
            'created': frame_data(lambda x: arrow.get(x['created_at']).floor(args.frame).datetime),  # Necessary to rate-limit data
            group: framed_data
        }
        
        frame = pd.DataFrame(dataframe_dict)

        if frame.empty:
            sys.stderr.write('No data to use! Try increasing the rate limit\n')
            sys.exit(1)

        compare_data = None
        data = None
        data_custom_title = None
        compare_data_custom_title = None

        if rate_limit:
            time = rate_limit[0][:-1]
            if args.compare_current:
                recent_start = arrow.utcnow().floor(time).datetime
                previous_start = arrow.utcnow().shift(**{rate_limit[0]:-1}).floor(time).datetime
                data = frame[frame['created'] >= recent_start]
                compare_data = frame[frame['created'] >= previous_start]
                compare_data = compare_data[compare_data['created'] < recent_start]
                data_custom_title = "PR Life for %s PRs Created in %s of %s, By Lines %s" % (repo, time.capitalize(), arrow.get(recent_start).format('MMM DD'), group)
                compare_data_custom_title = \
                    "PR Life for %s PRs Created in %s of %s, By Lines %s" % (repo, time.capitalize(), arrow.get(previous_start).format('MMM DD'), group)
            elif args.compare_last:
                current_start = arrow.utcnow().floor(time).datetime
                recent_start = arrow.utcnow().shift(**{rate_limit[0]:-1}).floor(time).datetime
                previous_start = arrow.utcnow().shift(**{rate_limit[0]:-2}).floor(time).datetime
                data = frame[frame['created'] < current_start]
                data = data[data['created'] >= recent_start]
                compare_data = frame[frame['created'] >= previous_start]
                compare_data = compare_data[compare_data['created'] < recent_start]
                data_custom_title = "PR Life for %s PRs Created in %s of %s, By Lines %s" % (repo, time.capitalize(), arrow.get(recent_start).format('MMM DD'), group)
                compare_data_custom_title = \
                    "PR Life for %s PRs Created in %s of %s, By Lines %s" % (repo, time.capitalize(), arrow.get(previous_start).format('MMM DD'), group)
            else:
                if args.limit_by_months and args.frame == 'week':
                    shift_time = rate_limit[1] * 4
                else:
                    shift_time = rate_limit[1]
                shift = {rate_limit[0]: shift_time}
                limited = arrow.utcnow().shift(**shift).floor(time)
                data = frame[frame['created'] >= limited.datetime]
            if data.empty:
                sys.stderr.write('No data to show!\n')
                sys.exit(1)
            if compare_data is not None and compare_data.empty:
                sys.stderr.write('No data to show!\n')
                sys.exit(1)
        else:
            data = frame

        if is_datetime:
            bar_width = (arrow.now().ceil(args.frame) - arrow.now().floor(args.frame)).total_seconds() * 800
            data = data['lifetime'].groupby(data[group])
        else:
            bar_width = args.round_to
            get_grouped_data = lambda data: data[data[group] < (args.round_to * 50)]['lifetime'].groupby(data[group])
            data = get_grouped_data(data)
            if compare_data is not None:
                compare_data = get_grouped_data(compare_data)
                compare_data = compare_data.apply(stats).unstack().to_dict()
        
        data = data.apply(stats).unstack().to_dict()

        get_graph_params = lambda data: data_to_graph_params(data, bar_width, {'count': 'PRs Completed'}, args.complete)
        line, bar = get_graph_params(data)
    
        if compare_data:
            bar['count']['x'] = list(map(lambda x: x + args.round_to/2, bar['count']['x']))  # Offset the bar x location for line analysis graphs
        
        chart_data.append(graph(line, bar, repo, args.frame, group, x_axis, y_axis, num_prs_y_axis, is_datetime, data_custom_title))

        if args.link_x:
            x_axis = chart_data[-1][0].x_range
        if args.link_y:
            y_axis = chart_data[-1][0].y_range
            num_prs_y_axis = chart_data[-1][1].y_range

        if compare_data:
            line, bar = get_graph_params(compare_data)
            bar['count']['x'] = list(map(lambda x: x + args.round_to/2, bar['count']['x']))
            chart_data.append(graph(line, bar, repo, args.frame, group, x_axis, y_axis, num_prs_y_axis, is_datetime, compare_data_custom_title))


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
    