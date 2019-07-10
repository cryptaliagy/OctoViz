import argparse
from octoviz.flush import flush
from octoviz.run import run
from octoviz.profile import profile_list, profile_delete, profile_create_update

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