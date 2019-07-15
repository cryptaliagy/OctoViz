from octoviz.common import clients_from_profiles, octoviz_dir, create_directory, get_raw_pull_data
from octoviz.graph import data_to_graph_params, graph

from bokeh.plotting import output_file, show
from bokeh.layouts import gridplot

import os, json, datetime, sys
import shutil

import arrow
import pandas as pd

def custom_percentiles(args):
    return sorted([int(p) for p in args.percentiles.split(',')])


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
        file_name = octoviz_dir('html/%s.html' % args.name)
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
        elif group == 'created':
            pass
        else:  # Default to fall back to
            group = 'closed'
            framed_data = frame_data(lambda x: arrow.get(x['closed_at']).floor(args.frame).datetime)

        # Build pandas frame
        dataframe_dict = {
            'pull number': frame_data(lambda x: x['number']),
            'lifetime': frame_data(lambda x: (arrow.get(x['closed_at']) - arrow.get(x['created_at'])).total_seconds()/3600/24),
            'created': frame_data(lambda x: arrow.get(x['created_at']).floor(args.frame).datetime),  # Necessary to rate-limit data
        }
        
        if group != 'created':
            dataframe_dict[group] = framed_data
        
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

        get_graph_params = lambda data: data_to_graph_params(data, bar_width, {'count': 'PRs Completed'}, is_datetime, args.round_to, args.complete)
        line, bar = get_graph_params(data)
    
        if not is_datetime:
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