import json, os, sys, re
from octoviz.common import octoviz_dir, make_github_client, create_directory, write_profile, load_profile, get_all_profiles

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