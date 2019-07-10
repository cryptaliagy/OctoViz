import github3, arrow
import os, sys, datetime, argparse, json, re, shutil
import itertools
from bokeh.plotting import figure, output_file, show
from bokeh.layouts import gridplot, row
from bokeh.palettes import Category10 as palette
from functools import reduce
import pandas as pd

def get_raw_pull_data(organization, repository, url=None):
    if url:
        client = github3.enterprise_login(token=token, url=url)
    else:
        client = github3.login(token=token)
    repo = client.repository(organization, repository)
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
        match = re.match('([0-9][0-9])th', param)
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


def graph(line_data, bar_data, repository_name, frame, x_range=None, y_range=None):
    line_chart = figure(
        title="Pull Request Data for %s, Aggregated by %s" % (repository_name.capitalize(), frame.capitalize()),
        x_axis_label="Date", 
        y_axis_label='Time to close PR (days)', 
        x_axis_type="datetime")
    if x_range is not None:
        line_chart.x_range = x_range
    if y_range is not None:
        line_chart.y_range = y_range

    bar_chart = figure(
        title="Pull Request Data for %s Aggregated by %s" % (repository_name.capitalize(), frame.capitalize()), 
        x_axis_label='Date', 
        x_axis_type="datetime", 
        x_range=line_chart.x_range)
    
    for key in line_data.keys():
        line_chart.line(line_width=2, **line_data[key])
    
    for key in bar_data.keys():
        bar_chart.vbar(**bar_data[key])
    
    line_chart.legend.click_policy = 'hide'

    return [line_chart, bar_chart]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='A tool to visualize Github data')

    parser.add_argument('-m', '--month', dest='frame', action='store_const', const='month', default='week', help='aggregate data by month (default: by week)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-b', '--build-cache', dest='cache', action='store_true', help='force the cache to be built, overriding any currently cached data')
    group.add_argument('--no-cache', dest="fetch_no_cache", action='store_true', help='force fetch the data but do not write it to a local cache')
    parser.add_argument('-rm', '--remove', action='store_true', help='remove cached data after execution')
    parser.add_argument('-x', '--link-x-axis', dest="link_x", action='store_true', help='Link the x-axis of all generated graphs')
    parser.add_argument('-y', '--link-y-axis', dest="link_y", action='store_true', help='Link the y-axis of all line graphs')
    parser.add_argument('-u', '--url', action='store', nargs=1, help="The url to use (if in a corporate environment)", default=[None])
    parser.add_argument('-t', '--token', action='store', nargs=1, help="OAuth token to use (overrides environment-specified token)", default=[None])
    parser.add_argument('repos', metavar='repository', nargs="+", help="the repositories to pull data from")

    args = parser.parse_args()

    if args.token[0]:
        token = args.token[0]
    else:
        token = os.getenv('GITHUB_API_TOKEN')
    
    if args.url[0]:
        url = args.url[0]
    else:
        url = os.getenv('GITHUB_URL')
    
    pull_data = []
    chart_data = []
    x_axis = None
    y_axis = None
    frame_data = lambda func, iterable: list(map(func, iterable))
    stats = lambda group: {'25th': group.quantile(0.25), '50th': group.median(), '90th': group.quantile(0.9), 'count': group.count()}

    for repository in args.repos:
        org, repo = repository.split('/') 

        # Build cache if force or if the cache does not exist
        if args.fetch_no_cache or args.cache or not os.path.exists('.cache/%s/%s.json' % (org, repo)):
            if not os.path.exists('.cache'):
                os.mkdir('.cache')
            if not os.path.exists('.cache/%s' % org):
                os.mkdir('.cache/%s' % org)

            pull_data = get_raw_pull_data(org, repo, url)

            
            if not args.fetch_no_cache:
                with open('.cache/%s.json' % repository, "w") as f:
                    json.dump(pull_data, f)
        # Read from cache files if they exist and not force-rebuild
        else:
            with open('.cache/%s.json' % repository, "r") as f:
                pull_data = json.load(f)
        
        # Build pandas frame
        frame = pd.DataFrame(
            {
                'Pull Number': frame_data(lambda x: x['number'], pull_data),
                'Created At': frame_data(lambda x: arrow.get(x['created_at']).floor(args.frame).datetime, pull_data),
                'Closed At': frame_data(lambda x: arrow.get(x['closed_at']).floor(args.frame).datetime, pull_data),
                'User': frame_data(lambda x: x['user']['login'], pull_data),
                'Lifetime': frame_data(lambda x: (arrow.get(x['closed_at']) - arrow.get(x['created_at'])).total_seconds()/3600/24, pull_data)
            }
        )
        
        bar_width = (arrow.now().ceil(args.frame) - arrow.now().floor(args.frame)).total_seconds() * 800
        data = frame['Lifetime'].groupby(frame['Closed At']).apply(stats).unstack().to_dict()
        line, bar = data_to_graph_params(data, bar_width, {'count': 'PRs Completed'})
        chart_data.append(graph(line, bar, repo, args.frame, x_axis, y_axis))

        if args.link_x:
            x_axis = charts_data[-1][0].x_range
        if args.link_y:
            y_axis = charts_data[-1][0].y_range

    
    if args.remove:
        shutil.rmtree('.cache', ignore_errors=True)
    
    show(gridplot(chart_data))
    
